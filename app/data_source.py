import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
import time

class TwelveDataClient:
    BASE_URL = "https://api.twelvedata.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_time_series(self, symbol: str, interval: str = "1min", outputsize: int = 120) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data. symbol like 'EUR/USD'"""
        if not self.api_key:
            return None
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self.api_key,
            "format": "JSON"
        }
        try:
            r = self.session.get(f"{self.BASE_URL}/time_series", params=params, timeout=15)
            data = r.json()
            if "values" not in data:
                print(f"Twelve Data error for {symbol}: {data.get('message', data)}")
                return None
            df = pd.DataFrame(data["values"])
            df = df.rename(columns={"datetime": "Datetime", "open": "Open", "high": "High", "low": "Low", "close": "Close"})
            df["Datetime"] = pd.to_datetime(df["Datetime"])
            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.sort_values("Datetime").reset_index(drop=True)
            return df
        except Exception as e:
            print(f"Twelve Data request failed for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        params = {"symbol": symbol, "apikey": self.api_key}
        try:
            r = self.session.get(f"{self.BASE_URL}/quote", params=params, timeout=10)
            return r.json()
        except Exception:
            return None
