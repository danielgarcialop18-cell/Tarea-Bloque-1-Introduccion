# cli.py — Punto de entrada principal
# -----------------------------------
# Aquí podrás probar tus extractores, normalizadores y reportes.
#
# Ejemplo:
# from extractors.alphavantage_extractor import AlphaVantageExtractor
# ex = AlphaVantageExtractor(apikey="TU_API_KEY")
# data = ex.history("AAPL")
# print(data)

import argparse

from .extractors.alphavantage_extractor import AlphaVantageExtractor
from .extractors.marketstack_extractor import MarketStackExtractor
from .extractors.twelvedata_extractor import TwelveDataExtractor
from .normalization.normalizer import Normalizer

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", choices=["alpha","marketstack","twelvedata"], required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--apikey", required=True)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    args = p.parse_args()

    if args.provider == "alpha":
        ex = AlphaVantageExtractor(args.apikey)
        raw = ex.history(args.symbol, start=args.start, end=args.end)
        rows = Normalizer().normalize_alphavantage_daily(raw, args.symbol)
        import pandas as pd
        df = pd.DataFrame(rows)
    elif args.provider == "marketstack":
        ex = MarketStackExtractor(args.apikey)
        raw = ex.history(args.symbol, start=args.start, end=args.end)
        rows = Normalizer().normalize_marketstack_eod(raw)
        import pandas as pd
        df = pd.DataFrame(rows)
    else:
        ex = TwelveDataExtractor(args.apikey)
        raw = ex.history(args.symbol, start=args.start, end=args.end)
        rows = Normalizer().normalize_twelvedata_timeseries(raw, args.symbol)
        import pandas as pd
        df = pd.DataFrame(rows)

    print("\n📊 Datos normalizados:\n")
    print(df.head().to_string())   # <-- esta es la parte importante
    print(f"\nTotal de filas: {len(df)}")
    print(f"Rango de fechas: {df.index.min().date()} → {df.index.max().date()}")

    print("Primeras 5 filas:", rows[:5])
    print("Últimas 5 filas:", rows[-5:])


if __name__ == "__main__":
    main()
