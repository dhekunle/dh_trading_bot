"""
Data helpers using yfinance (no API key required).
"""
import yfinance as yf
import pandas as pd
from typing import Optional

def get_history(symbol: str, period: str = "2d", interval: str = "1m") -> Optional[pd.DataFrame]:
    """Fetch OHLCV using yfinance. symbol like 'EURUSD=X'"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist is None or hist.empty or len(hist) < 30:
            return None
        hist = hist.reset_index()
        hist = hist.rename(columns={"Datetime": "Datetime", "Open": "Open", "High": "High", "Low": "Low", "Close": "Close"})
        return hist
    except Exception as e:
        print(f"yfinance error for {symbol}: {e}")
        return None
