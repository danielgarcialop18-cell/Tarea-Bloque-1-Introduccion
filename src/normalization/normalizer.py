import pandas as pd

from datetime import datetime
from dateutil import parser

STANDARD_COLS = ["date","open","high","low","close","volume","ticker","source"]

class Normalizer:
    def _dt(self, s):  # string -> datetime naive
        if isinstance(s, datetime): return s
        dt = parser.isoparse(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    def normalize_alphavantage_daily(self, raw: dict, ticker: str):
        # Busca "Time Series (Daily)"
        ts = None
        for k in raw.keys():
            if "Time Series" in k:
                ts = raw[k]; break
        if ts is None: return []
        out = []
        for d, row in ts.items():
            out.append({
                "date": self._dt(d),
                "open": float(row.get("1. open", "nan")),
                "high": float(row.get("2. high", "nan")),
                "low":  float(row.get("3. low", "nan")),
                "close":float(row.get("4. close", "nan")),
                "volume": float(row.get("5. volume", "nan")),
                "ticker": ticker,
                "source": "alphavantage",
            })
        df = pd.DataFrame(sorted(out, key=lambda x: x["date"]))
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def normalize_marketstack_eod(self, raw: dict):
        data = raw.get("data", [])
        out = []
        for r in data:
            out.append({
                "date": self._dt(r.get("date")),
                "open": float(r["open"]) if r.get("open") is not None else float("nan"),
                "high": float(r["high"]) if r.get("high") is not None else float("nan"),
                "low":  float(r["low"])  if r.get("low")  is not None else float("nan"),
                "close":float(r["close"])if r.get("close")is not None else float("nan"),
                "volume": float(r["volume"]) if r.get("volume") is not None else float("nan"),
                "ticker": r.get("symbol"),
                "source": "marketstack",
            })
        df = pd.DataFrame(sorted(out, key=lambda x: x["date"]))
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def normalize_twelvedata_timeseries(self, raw: dict, ticker: str):
        vals = raw.get("values", [])
        out = []
        for r in vals:
            out.append({
                "date": self._dt(r.get("datetime")),
                "open": float(r["open"]) if r.get("open") is not None else float("nan"),
                "high": float(r["high"]) if r.get("high") is not None else float("nan"),
                "low":  float(r["low"])  if r.get("low")  is not None else float("nan"),
                "close":float(r["close"])if r.get("close")is not None else float("nan"),
                "volume": float(r["volume"]) if r.get("volume") is not None else float("nan"),
                "ticker": ticker,
                "source": "twelvedata",
            })
        df = pd.DataFrame(sorted(out, key=lambda x: x["date"]))
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df
