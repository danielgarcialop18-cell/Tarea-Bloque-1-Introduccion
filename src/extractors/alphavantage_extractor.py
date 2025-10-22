import requests
from .base import BaseExtractor

class AlphaVantageExtractor(BaseExtractor):
    BASE = "https://www.alphavantage.co/query"
    def __init__(self, apikey: str):
        self.apikey = apikey

    def history(self, ticker: str, start: str | None = None, end: str | None = None):
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "apikey": self.apikey,
            "outputsize": "full",
        }
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def quote(self, symbol: str):
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.apikey}
        r = requests.get(self.BASE, params=params, timeout=30); r.raise_for_status()
        return r.json()
    
    def rsi(self, symbol: str, time_period: int = 14, interval: str = "daily", series_type: str = "close"):
        params = {
            "function": "RSI",
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "series_type": series_type,
             "apikey": self.apikey,
        }
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

