import argparse
import os
import sys
import pandas as pd

from .extractors.alphavantage_extractor import AlphaVantageExtractor
from .extractors.marketstack_extractor import MarketStackExtractor
from .extractors.twelvedata_extractor import TwelveDataExtractor
from .normalization.normalizer import Normalizer


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
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    apikey = _resolve_api_key(args.provider, args.apikey)
    ex = _get_extractor(args.provider, apikey)
    norm = Normalizer()

    if args.datatype == "history":
        dfs = []
        for sym in symbols:
            raw = ex.history(sym, start=args.start, end=args.end)
            if args.provider == "alpha":
                df = norm.normalize_alphavantage_daily(raw, sym)
            elif args.provider == "marketstack":
                df = norm.normalize_marketstack_eod(raw)
            else:
                df = norm.normalize_twelvedata_timeseries(raw, sym)
            dfs.append(df)
        out = _concat_or_single(dfs)

    else:  # indicator == "rsi"
        dfs = []
        for sym in symbols:
            if args.provider == "alpha":
                raw = ex.rsi(sym, time_period=args.time_period, interval="daily", series_type="close")
                df = norm.normalize_alphavantage_rsi(raw, sym)
            elif args.provider == "twelvedata":
                raw = ex.rsi(sym, time_period=args.time_period, interval="1day")
                df = norm.normalize_twelvedata_rsi(raw, sym)
            else:
                print("⚠️ MarketStack no ofrece RSI gratuito; omitiendo.", file=sys.stderr)
                df = pd.DataFrame()
            dfs.append(df)
        out = _concat_or_single(dfs)

    # Salida por pantalla
    if out is None or out.empty:
        print("⛔ No hay datos para mostrar.")
    else:
        print("📊 Datos normalizados (head):\n")
        print(out.head().to_string())
        print(f"\nFilas: {len(out)}")
        if "ticker" in out.columns:
            print("Tickers en salida:", sorted(out["ticker"].dropna().unique().tolist()))

    # Persistencia opcional
    if args.to_csv:
        out.to_csv(args.to_csv, index=True)
        print(f"💾 Guardado CSV en: {args.to_csv}")
    if args.to_json:
        out.to_json(args.to_json, orient="records", date_format="iso")
        print(f"💾 Guardado JSON en: {args.to_json}")


if __name__ == "__main__":
    main()
