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
