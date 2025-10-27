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
from .models.series import PriceSeries, Portfolio

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
    
    # --- CAMBIO: NUEVOS ARGUMENTOS ESTADÍSTICOS ---
    p.add_argument("--show-stats", action="store_true", 
                   help="Muestra estadísticas adicionales (min/max, retorno medio)")
    p.add_argument("--sma", type=int, default=None, 
                   help="Calcula y muestra la SMA de N días (ej. 20 o 50)")

    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    apikey = _resolve_api_key(args.provider, args.apikey)
    ex = _get_extractor(args.provider, apikey)
    norm = Normalizer()
    
    out_by_symbol: dict[str, pd.DataFrame] = {} 

    # --- (AQUÍ VA TODA LA LÓGICA DE DESCARGA (HISTORY / INDICATOR) ... ) ---
    # --- ( ... ESA PARTE NO CAMBIA ... ) ---
    # ---------- HISTÓRICO (OHLCV) ----------
    if args.datatype == "history":
        fetch_one = lambda s: ex.history(s, start=args.start, end=args.end)
        if args.provider == "alpha":
            normalize_one = lambda raw, s: norm.normalize_alphavantage_daily(raw, s)
        elif args.provider == "marketstack":
            normalize_one = lambda raw, s: norm.normalize_marketstack_eod(raw)
        else:  # twelvedata
            normalize_one = lambda raw, s: norm.normalize_twelvedata_timeseries(raw, s)

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
    
    
    # ---------- CREACIÓN DE OBJETOS Portfolio y PriceSeries ---------- 
    # (Esta parte no cambia)
    portfolio_name = f"Cartera CLI ({args.provider} - {args.datatype})"
    cartera = Portfolio(name=portfolio_name)
    
    for sym, df in out_by_symbol.items():
        if df is not None and not df.empty:
            source = df['source'].iloc[0] if 'source' in df.columns else args.provider
            serie = PriceSeries(ticker=sym, source=source, data=df)
            cartera.add_series(serie)

    # ---------- Unimos todo en un DataFrame para exportar (opcional) ----------
    # (Esta parte no cambia)
    out = _concat_or_single(list(out_by_symbol.values()))


    # ---------- Salida por pantalla (Modificada) ---------- #
    
    if not cartera.assets: 
        print("\n⛔ No hay datos para mostrar.")
    else:
        print("\n" + "="*40)
        print(f"📊 Resumen de la Cartera: '{cartera.name}'")
        print(f"Total de activos: {len(cartera)}")
        print("="*40)

        # --- CAMBIO: BUCLE DE IMPRESIÓN MEJORADO ---
        for ticker, series in cartera.assets.items():
            
            # 1. Imprimir el resumen (que ahora incluye media/std automáticamente)
            print(f"\n  -> {series.get_summary()}") # Pongo \n para separar cada activo
            
            # 2. Comprobar y mostrar SMA si se pidió
            if args.sma:
                sma = series.calculate_sma(args.sma)
                if sma is not None and not sma.empty:
                    # .iloc[-1] coge el último valor de la media móvil
                    print(f"     SMA({args.sma}d): {sma.iloc[-1]:.2f}") 
                    
            # 3. Comprobar y mostrar más estadísticas si se pidió
            if args.show_stats:
                stats = series.get_min_max()
                returns = series.get_daily_returns()
                
                if stats:
                    print(f"     Mín: {stats['min_value']:.2f} (el {stats['min_date'].date()})")
                    print(f"     Máx: {stats['max_value']:.2f} (el {stats['max_date'].date()})")
                if returns is not None:
                    # .mean() * 100 para verlo en porcentaje
                    print(f"     Retorno Diario Medio: {returns.mean() * 100:.4f}%")
                        
        print("\n" + "="*40) # Añadido \n para espaciado


    # ---------- Persistencia opcional (Sin cambios) ----------
    if args.to_csv:
        out.to_csv(args.to_csv, index=True)
        print(f"💾 Guardado CSV combinado en: {args.to_csv}")
    if args.to_json:
        out.to_json(args.to_json, orient="records", date_format="iso")
        print(f"💾 Guardado JSON combinado en: {args.to_json}")


if __name__ == "__main__":
    main()