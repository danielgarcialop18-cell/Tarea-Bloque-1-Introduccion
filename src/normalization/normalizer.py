import pandas as pd
from datetime import datetime
from dateutil import parser

STANDARD_COLS = ["date","open","high","low","close","volume","ticker","source"]

class Normalizer:

    def _dt(self, s):  
        if isinstance(s, datetime): 
            return s
        dt = parser.isoparse(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    def _finalize_ohlcv(self, rows: list[dict]) -> pd.DataFrame:
        """Convierte lista de dicts OHLCV a DataFrame con index datetime ordenado."""
        df = pd.DataFrame(sorted(rows, key=lambda x: x["date"]))
        if df.empty:
            # DataFrame vacío pero con columnas estándar
            return pd.DataFrame(columns=STANDARD_COLS).set_index(pd.Index([], name="date"))
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")

    # --- OHLCV: AlphaVantage ---
    def normalize_alphavantage_daily(self, raw: dict, ticker: str) -> pd.DataFrame:
        # Busca "Time Series (Daily)"
        ts = None
        for k in raw.keys():
            if "Time Series" in k:
                ts = raw[k]
                break
        if ts is None:
            return pd.DataFrame(columns=STANDARD_COLS).set_index(pd.Index([], name="date"))

        out = []
        for d, row in ts.items():
            out.append({
                "date":   self._dt(d),
                "open":   float(row.get("1. open", "nan")),
                "high":   float(row.get("2. high", "nan")),
                "low":    float(row.get("3. low", "nan")),
                "close":  float(row.get("4. close", "nan")),
                "volume": float(row.get("5. volume", "nan")),
                "ticker": ticker,
                "source": "alphavantage",
            })
        return self._finalize_ohlcv(out)

    # --- OHLCV: MarketStack ---
    def normalize_marketstack_eod(self, raw: dict) -> pd.DataFrame:
        data = raw.get("data", [])
        out = []
        for r in data:
            out.append({
                "date":   self._dt(r.get("date")),
                "open":   float(r["open"])   if r.get("open")   is not None else float("nan"),
                "high":   float(r["high"])   if r.get("high")   is not None else float("nan"),
                "low":    float(r["low"])    if r.get("low")    is not None else float("nan"),
                "close":  float(r["close"])  if r.get("close")  is not None else float("nan"),
                "volume": float(r["volume"]) if r.get("volume") is not None else float("nan"),
                "ticker": r.get("symbol"),
                "source": "marketstack",
            })
        return self._finalize_ohlcv(out)

    # --- OHLCV: TwelveData ---
    def normalize_twelvedata_timeseries(self, raw: dict, ticker: str) -> pd.DataFrame:
        vals = raw.get("values", [])
        out = []
        for r in vals:
            out.append({
                "date":   self._dt(r.get("datetime")),
                "open":   float(r["open"])   if r.get("open")   is not None else float("nan"),
                "high":   float(r["high"])   if r.get("high")   is not None else float("nan"),
                "low":    float(r["low"])    if r.get("low")    is not None else float("nan"),
                "close":  float(r["close"])  if r.get("close")  is not None else float("nan"),
                "volume": float(r["volume"]) if r.get("volume") is not None else float("nan"),
                "ticker": ticker,
                "source": "twelvedata",
            })
        return self._finalize_ohlcv(out)


    # --- INDICADORES (RSI) ---
    
    def normalize_alphavantage_rsi(self, raw: dict, ticker: str) -> pd.DataFrame:
        """
        AlphaVantage: el RSI viene bajo la clave 'Technical Analysis: RSI'.
        Devuelve DF con índice 'date' y columna 'rsi'.
        """
        block = raw.get("Technical Analysis: RSI", {})
        rows = []
        for d, obj in block.items():
            # obj típicamente: {"RSI": "56.1234"}
            val_str = obj.get("RSI")
            try:
                val = float(val_str) if val_str is not None else float("nan")
            except:
                val = float("nan")
            rows.append({"date": self._dt(d), "rsi": val, "ticker": ticker, "source": "alphavantage"})
        df = pd.DataFrame(rows).sort_values("date")
        if df.empty:
            return pd.DataFrame(columns=["rsi", "ticker", "source"]).set_index(pd.Index([], name="date"))
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")

    def normalize_twelvedata_rsi(self, raw: dict, ticker: str) -> pd.DataFrame:
        """
        TwelveData: el RSI viene en 'values' con pares {'datetime': ..., 'rsi': '...'}.
        Devuelve DF con índice 'date' y columna 'rsi'.
        """
        vals = raw.get("values", []) or []
        rows = []
        for r in vals:
            val_str = r.get("rsi")
            try:
                val = float(val_str) if val_str is not None else float("nan")
            except:
                val = float("nan")
            rows.append({"date": self._dt(r.get("datetime")), "rsi": val, "ticker": ticker, "source": "twelvedata"})
        df = pd.DataFrame(rows).sort_values("date")
        if df.empty:
            return pd.DataFrame(columns=["rsi", "ticker", "source"]).set_index(pd.Index([], name="date"))
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")

    # Une los precios por fecha
    def attach_indicator(self, prices_df: pd.DataFrame, ind_df: pd.DataFrame, col_name: str = "rsi") -> pd.DataFrame:
        """
        Hace un merge por índice fecha y añade la columna del indicador al DF de precios.
        Útil para visualizar/guardar todo junto.
        """
        if prices_df is None or prices_df.empty:
            return ind_df.rename(columns={col_name: f"{col_name}"})
        if ind_df is None or ind_df.empty:
            return prices_df
        merged = prices_df.join(ind_df[[col_name]], how="left")
        return merged
