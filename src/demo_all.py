# src/demo_all.py
"""
Demo de todo lo implementado:
- OHLCV (AlphaVantage, MarketStack, TwelveData)
- RSI (AlphaVantage, TwelveData)
Uso:
    python -m src.demo_all --symbols AAPL,MSFT --start 2024-01-01 --end 2024-03-31 \
        --alpha-key TU_ALPHA --marketstack-key TU_MS --twelve-key TU_TWELVE
O (más cómodo) con variables de entorno:
    set ALPHAVANTAGE_API_KEY=...
    set MARKETSTACK_API_KEY=...
    set TWELVEDATA_API_KEY=...
    python -m src.demo_all --symbols AAPL,MSFT --start 2024-01-01 --end 2024-03-31
"""

from __future__ import annotations
import os
import argparse
import pandas as pd

# Importa tus extractores y normalizador
from extractors.alphavantage_extractor import AlphaVantageExtractor
from extractors.marketstack_extractor import MarketStackExtractor
from extractors.twelvedata_extractor import TwelveDataExtractor
from normalization.normalizer import Normalizer


def _k(name: str, cli_value: str | None) -> str | None:
    """Devuelve la API key: primero CLI, si no, variable de entorno."""
    if cli_value:
        return cli_value
    env_map = {
        "alpha": "ALPHAVANTAGE_API_KEY",
        "marketstack": "MARKETSTACK_API_KEY",
        "twelvedata": "TWELVEDATA_API_KEY",
    }
    return os.getenv(env_map[name])



def _print_section(title: str):
    print("\n" + "=" * (len(title) + 4))
    print(f"= {title} =")
    print("=" * (len(title) + 4) + "\n")


def _print_df(df: pd.DataFrame, n: int = 5):
    if df is None or df.empty:
        print("(DataFrame vacío)")
        return
    # Mostrar columnas y un head formateado
    print("Columnas:", list(df.columns))
    print(df.head(n).to_string())


def test_alpha(symbols: list[str], start: str | None, end: str | None, apikey: str):
    _print_section("AlphaVantage - OHLCV + RSI")
    norm = Normalizer()
    ex = AlphaVantageExtractor(apikey=apikey)

    for sym in symbols:
        print(f"\n--- {sym} (OHLCV) ---")
        try:
            raw = ex.history(sym, start=start, end=end)  # Alpha ignora fechas en URL; filtraremos luego si quieres
            df = norm.normalize_alphavantage_daily(raw, sym)
            # Filtrado opcional por rango (por si pasaste start/end)
            if start or end:
                df = df.loc[(start or df.index.min()):(end or df.index.max())]
            _print_df(df)
            print(f"Filas: {len(df)} | Rango: {df.index.min().date()} → {df.index.max().date()}")
        except Exception as e:
            print(f"⚠️ Error AlphaVantage OHLCV {sym}: {e}")

        print(f"\n--- {sym} (RSI 14) ---")
        try:
            raw_rsi = ex.rsi(sym, time_period=14, interval="daily", series_type="close")
            df_rsi = norm.normalize_alphavantage_rsi(raw_rsi, sym)
            _print_df(df_rsi)
            if not df_rsi.empty:
                print(f"Filas RSI: {len(df_rsi)} | Última fecha: {df_rsi.index.max().date()}")
        except Exception as e:
            print(f"⚠️ Error AlphaVantage RSI {sym}: {e}")


def test_marketstack(symbols: list[str], start: str | None, end: str | None, apikey: str):
    _print_section("MarketStack - OHLCV")
    norm = Normalizer()
    ex = MarketStackExtractor(apikey=apikey)

    for sym in symbols:
        print(f"\n--- {sym} (OHLCV) ---")
        try:
            raw = ex.history(sym, start=start, end=end)
            df = norm.normalize_marketstack_eod(raw)
            _print_df(df)
            if not df.empty:
                print(f"Filas: {len(df)} | Rango: {df.index.min().date()} → {df.index.max().date()}")
        except Exception as e:
            print(f"⚠️ Error MarketStack OHLCV {sym}: {e}")


def test_twelvedata(symbols: list[str], start: str | None, end: str | None, apikey: str):
    _print_section("TwelveData - OHLCV + RSI")
    norm = Normalizer()
    ex = TwelveDataExtractor(apikey=apikey)

    for sym in symbols:
        print(f"\n--- {sym} (OHLCV) ---")
        try:
            raw = ex.history(sym, start=start, end=end)
            df = norm.normalize_twelvedata_timeseries(raw, sym)
            _print_df(df)
            if not df.empty:
                print(f"Filas: {len(df)} | Rango: {df.index.min().date()} → {df.index.max().date()}")
        except Exception as e:
            print(f"⚠️ Error TwelveData OHLCV {sym}: {e}")

        print(f"\n--- {sym} (RSI 14) ---")
        try:
            raw_rsi = ex.rsi(sym, time_period=14, interval="1day")
            df_rsi = norm.normalize_twelvedata_rsi(raw_rsi, sym)
            _print_df(df_rsi)
            if not df_rsi.empty:
                print(f"Filas RSI: {len(df_rsi)} | Última fecha: {df_rsi.index.max().date()}")
        except Exception as e:
            print(f"⚠️ Error TwelveData RSI {sym}: {e}")


def main():
    p = argparse.ArgumentParser(description="Smoke test de extractores + normalizador (OHLCV y RSI)")
    p.add_argument("--symbols", default="AAPL", help="Símbolos separados por comas (ej. AAPL,MSFT,EUR/USD)")
    p.add_argument("--start", default=None, help="YYYY-MM-DD (opcional)")
    p.add_argument("--end", default=None, help="YYYY-MM-DD (opcional)")

    # API keys (CLI o variables de entorno)
    p.add_argument("--alpha-key", default=None)
    p.add_argument("--marketstack-key", default=None)
    p.add_argument("--twelve-key", default=None)

    # Qué proveedores probar (por defecto todos los disponibles)
    p.add_argument("--providers", default="alpha,marketstack,twelvedata",
                   help="Lista separada por comas: alpha,marketstack,twelvedata")

    args = p.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]

    alpha_key = _k("alpha", args.alpha_key)
    ms_key = _k("marketstack", args.marketstack_key)
    td_key = _k("twelvedata", args.twelve_key)

    if "alpha" in providers:
        if alpha_key:
            test_alpha(symbols, args.start, args.end, alpha_key)
        else:
            print("\n⛔ AlphaVantage omitido: falta API key (ALPHAVANTAGE_API_KEY o --alpha-key)")

    if "marketstack" in providers:
        if ms_key:
            test_marketstack(symbols, args.start, args.end, ms_key)
        else:
            print("\n⛔ MarketStack omitido: falta API key (MARKETSTACK_API_KEY o --marketstack-key)")

    if "twelvedata" in providers:
        if td_key:
            test_twelvedata(symbols, args.start, args.end, td_key)
        else:
            print("\n⛔ TwelveData omitido: falta API key (TWELVEDATA_API_KEY o --twelve-key)")

    print("\n✅ Fin del demo. Si algún bloque salió con ⚠️, revisa el mensaje de error (clave inválida, límite de rate, símbolo, etc.).")


if __name__ == "__main__":
    main()
