import requests
from .base import BaseExtractor

class MarketStackExtractor(BaseExtractor):
    BASE = "http://api.marketstack.com/v1/eod"
    def __init__(self, apikey: str):
        self.apikey = apikey

    def entrada(self, ticker: str, start: str | None = None, end: str | None = None):
        params = {
            "access_key": self.apikey,
            "symbols": ticker,
            "date_from": start,
            "date_to": end,
            "limit": 1000,
        }
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
