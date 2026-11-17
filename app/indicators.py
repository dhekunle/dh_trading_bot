"""
Technical indicators written with plain pandas/numpy.

These follow the standard definitions (Wilder smoothing for RSI, ATR and ADX,
population standard deviation for Bollinger Bands) so the signals match what
pandas_ta produced in the original scripts, without needing that library.
"""
import numpy as np
import pandas as pd


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length).mean()


def rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's smoothing."""
    return series.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    return rma(true_range(high, low, close), length)


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # No losses at all in the window means RSI is 100
    out = out.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    return out


def bbands(close: pd.Series, length: int = 20, std: float = 2.0):
    """Returns (upper, middle, lower)."""
    mid = sma(close, length)
    dev = close.rolling(length).std(ddof=0)
    return mid + std * dev, mid, mid - std * dev


def stoch(high: pd.Series, low: pd.Series, close: pd.Series,
          k: int = 5, d: int = 3, smooth_k: int = 3):
    """Returns (%K, %D) using the same smoothing as pandas_ta.stoch."""
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    spread = (highest - lowest).replace(0, np.nan)
    raw_k = 100 * (close - lowest) / spread
    k_line = sma(raw_k, smooth_k)
    d_line = sma(k_line, d)
    return k_line, d_line


def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)
    atr_val = rma(true_range(high, low, close), length)
    plus_di = 100 * rma(plus_dm, length) / atr_val
    minus_di = 100 * rma(minus_dm, length) / atr_val
    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denom
    return rma(dx, length)
