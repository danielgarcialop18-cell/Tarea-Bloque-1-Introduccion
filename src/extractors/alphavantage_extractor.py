import requests
from .base import BaseExtractor

class AlphaVantageExtractor(BaseExtractor):
    BASE = "https://www.alphavantage.co/query"
    def __init__(self, apikey: str):
        self.apikey = apikey

    def history(self, ticker: str, start: str | None = None, end: str | None = None):
        params = {
            "function": "TIME_SERIES_DAILY",
            "Ticker": ticker,
            "apikey": self.apikey,
            "outputsize": "full",
        }
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
