import requests
from .base import BaseExtractor

class TwelveDataExtractor(BaseExtractor):
    BASE = "https://api.twelvedata.com/time_series"
    def __init__(self, apikey: str):
        self.apikey = apikey

    def history(self, symbol: str, start: str | None = None, end: str | None = None):
        params = {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 5000,
            "apikey": self.apikey,
        }
        if start: params["start_date"] = start
        if end: params["end_date"] = end
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def quote(self, symbol: str):
        params = {"symbol": symbol, "apikey": self.apikey}
        r = requests.get(self.QUOTE, params=params, timeout=30); r.raise_for_status()
        return r.json()
    
    def rsi(self, symbol: str, time_period: int = 14, interval: str = "1day"):
        params = {
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": self.apikey,
        }
        r = requests.get("https://api.twelvedata.com/rsi", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

