import argparse
import os
import sys
import pandas as pd

from .extractors.alphavantage_extractor import AlphaVantageExtractor
from .extractors.marketstack_extractor import MarketStackExtractor
from .extractors.twelvedata_extractor import TwelveDataExtractor
from .extractors.runner import fetch_many
from .normalization.normalizer import Normalizer
# Importa las nuevas clases del modelo que creaste
from .models.series import PriceSeries, Portfolio  # <--- CAMBIO

def _get_extractor(provider: str, apikey: str):
    if provider == "alpha":
        return AlphaVantageExtractor(apikey)
    elif provider == "marketstack":
        return MarketStackExtractor(apikey)
    elif provider == "twelvedata":
        return TwelveDataExtractor(apikey)
    else:
        raise SystemExit(f"Proveedor no soportado: {provider}")


def _resolve_api_key(provider: str, apikey_arg: str | None) -> str:
    if apikey_arg:
        return apikey_arg
    env_map = {
        "alpha": "ALPHAVANTAGE_API_KEY",
        "marketstack": "MARKETSTACK_API_KEY",
        "twelvedata": "TWELVEDATA_API_KEY",
    }
    key = os.getenv(env_map[provider])
    if not key:
        raise SystemExit(f"Falta API key. Pasa --apikey o define {env_map[provider]}.")
    return key


def _concat_or_single(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    dfs = [df for df in dfs if df is not None and not df.empty]
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs).sort_index()


def main():
    p = argparse.ArgumentParser(description="Extractor multi-API de OHLCV y RSI (formato estandarizado)")
    p.add_argument("--provider", choices=["alpha","marketstack","twelvedata"], required=True,
                   help="Proveedor de datos")
    p.add_argument("--symbols", required=True,
                   help="Símbolos separados por comas (ej. AAPL,MSFT o índices como ^GSPC, EUR/USD en TwelveData)")
    p.add_argument("--datatype", choices=["history","indicator"], default="history",
                   help="Tipo de dato: histórico OHLCV o indicador")
    p.add_argument("--indicator", choices=["rsi"], default="rsi",
                   help="Indicador (si datatype=indicator)")
    p.add_argument("--time_period", type=int, default=14,
                   help="Periodo del indicador (por defecto 14)")
    p.add_argument("--start", default=None, help="YYYY-MM-DD (si la API lo soporta)")
    p.add_argument("--end", default=None, help="YYYY-MM-DD (si la API lo soporta)")
    p.add_argument("--apikey", default=None, help="API key (si no, se leerá de variable de entorno)")
    p.add_argument("--to-csv", default=None, help="Ruta de salida CSV (opcional)")
    p.add_argument("--to-json", default=None, help="Ruta de salida JSON (opcional)")
    p.add_argument("--max-workers", type=int, default=4,
                   help="Nº de descargas simultáneas (1 = secuencial)")
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    apikey = _resolve_api_key(args.provider, args.apikey)
    ex = _get_extractor(args.provider, apikey)
    norm = Normalizer()
    
    # Esta variable contendrá el resultado de fetch_many: Dict[str, pd.DataFrame]
    out_by_symbol: dict[str, pd.DataFrame] = {} # <--- CAMBIO (solo inicialización)

    # ---------- HISTÓRICO (OHLCV) ----------
    if args.datatype == "history":
        # Definimos cómo descargar 1 símbolo y cómo normalizarlo, según provider
        fetch_one = lambda s: ex.history(s, start=args.start, end=args.end)
        if args.provider == "alpha":
            normalize_one = lambda raw, s: norm.normalize_alphavantage_daily(raw, s)
        elif args.provider == "marketstack":
            normalize_one = lambda raw, s: norm.normalize_marketstack_eod(raw)
        else:  # twelvedata
            normalize_one = lambda raw, s: norm.normalize_twelvedata_timeseries(raw, s)

        # Elegimos secuencial vs paralelo
        if args.max_workers == 1:
            for sym in symbols:
                try:
                    raw = fetch_one(sym)
                    out_by_symbol[sym] = normalize_one(raw, sym)
                except Exception as e:
                    print(f"⚠️ Error con {sym}: {e}", file=sys.stderr)
                    out_by_symbol[sym] = pd.DataFrame()
        else:
            out_by_symbol = fetch_many(symbols, fetch_one, normalize_one, max_workers=args.max_workers)

    # ---------- INDICADORES (RSI) ----------
    else:
        if args.indicator != "rsi":
            raise SystemExit("Por ahora solo se implementa RSI en modo indicador.")
        # Definimos fetch/normalize de RSI según provider
        if args.provider == "alpha":
            fetch_one = lambda s: ex.rsi(s, time_period=args.time_period, interval="daily", series_type="close")
            normalize_one = lambda raw, s: norm.normalize_alphavantage_rsi(raw, s)
        elif args.provider == "twelvedata":
            fetch_one = lambda s: ex.rsi(s, time_period=args.time_period, interval="1day")
            normalize_one = lambda raw, s: norm.normalize_twelvedata_rsi(raw, s)
        else:
            print("⚠️ MarketStack no ofrece RSI gratuito; omitiendo.", file=sys.stderr)
            fetch_one = lambda s: {}
            normalize_one = lambda raw, s: pd.DataFrame()

        if args.max_workers == 1:
            for sym in symbols:
                try:
                    raw = fetch_one(sym)
                    out_by_symbol[sym] = normalize_one(raw, sym)
                except Exception as e:
                    print(f"⚠️ Error con {sym}: {e}", file=sys.stderr)
                    out_by_symbol[sym] = pd.DataFrame()
        else:
            out_by_symbol = fetch_many(symbols, fetch_one, normalize_one, max_workers=args.max_workers)
    
    
    # ---------- CREACIÓN DE OBJETOS Portfolio y PriceSeries ---------- # <--- CAMBIO (NUEVO BLOQUE)
    
    # 1. Creamos la cartera (el "archivador")
    portfolio_name = f"Cartera CLI ({args.provider} - {args.datatype})"
    cartera = Portfolio(name=portfolio_name)
    
    # 2. Iteramos sobre los DataFrames descargados
    for sym, df in out_by_symbol.items():
        if df is not None and not df.empty:
            # Obtenemos la fuente del propio DataFrame (gracias al normalizador)
            source = df['source'].iloc[0] if 'source' in df.columns else args.provider
            
            # Creamos la "ficha" (PriceSeries)
            serie = PriceSeries(ticker=sym, source=source, data=df)
            
            # Añadimos la "ficha" al "archivador"
            cartera.add_series(serie) # Esto imprimirá "Activo ... añadido a la cartera ..."

    # ---------- Unimos todo en un DataFrame para exportar (opcional) ----------
    # Mantenemos esta lógica para que --to-csv y --to-json sigan funcionando
    out = _concat_or_single(list(out_by_symbol.values()))


    # ---------- Salida por pantalla (Modificada) ---------- # <--- CAMBIO (BLOQUE MODIFICADO)
    
    if not cartera.assets: # Comprobamos si la cartera está vacía
        print("\n⛔ No hay datos para mostrar.")
    else:
        print("\n" + "="*40)
        print(f"📊 Resumen de la Cartera: '{cartera.name}'")
        print(f"Total de activos: {len(cartera)}")
        print("="*40)
        # Usamos el método get_summary() de cada serie
        for ticker, series in cartera.assets.items():
            print(f"  -> {series.get_summary()}")
        print("="*40)


    # ---------- Persistencia opcional (Sin cambios) ----------
    # Guardamos el DataFrame 'out' combinado, como antes.
    if args.to_csv:
        out.to_csv(args.to_csv, index=True)
        print(f"💾 Guardado CSV combinado en: {args.to_csv}")
    if args.to_json:
        out.to_json(args.to_json, orient="records", date_format="iso")
        print(f"💾 Guardado JSON combinado en: {args.to_json}")


if __name__ == "__main__":
    main()
