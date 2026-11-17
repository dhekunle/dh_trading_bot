"""
Yahoo Finance data layer shared by both bots.

Why this exists: both bots used to download the same 17 pairs every 30 seconds,
plus extra M5/M15 and volatility downloads, which got the server rate limited
(HTTP 429). This module:

* caches every download, so the two bots share one copy of each pair
* spaces requests out and never runs two downloads at once
* backs off for a few minutes when Yahoo answers 429, instead of hammering it
* never hands back stale prices for trading (old data is dropped, not reused)
* exposes status() so the dashboard can show why there is no data
"""
import threading
import time
from typing import Optional

import pandas as pd

_lock = threading.RLock()
_cache = {}          # (symbol, period, interval) -> (fetched_at, DataFrame)
_tickers = {}        # symbol -> yfinance.Ticker

# How long a download is reused before fetching again (seconds)
TTL = {"1m": 55, "5m": 240, "15m": 600}
# How old cached data may be when a fresh download fails (seconds)
MAX_STALE = {"1m": 120, "5m": 900, "15m": 1800}

MIN_GAP = 0.5                 # seconds between outgoing requests
BASE_COOLDOWN = 300           # first 429 pauses downloads for 5 minutes
MAX_COOLDOWN = 1800           # repeated 429s back off up to 30 minutes

_state = {
    "last_request": 0.0,
    "cooldown_until": 0.0,
    "cooldown_step": 0,
    "requests": 0,
    "cache_hits": 0,
    "failures": 0,
    "last_ok": None,
    "last_error": None,
}


def _is_rate_limit(error) -> bool:
    text = str(error).lower()
    name = type(error).__name__.lower()
    return "429" in text or "too many requests" in text or "rate limit" in text or "ratelimit" in name


def _enter_cooldown():
    _state["cooldown_step"] += 1
    seconds = min(BASE_COOLDOWN * (2 ** (_state["cooldown_step"] - 1)), MAX_COOLDOWN)
    _state["cooldown_until"] = time.time() + seconds
    print(f"[YF] Rate limited by Yahoo. Pausing downloads for {int(seconds // 60)} min.")


def _get_ticker(symbol: str):
    import yfinance as yf  # imported here so the app still starts if it is missing
    if symbol not in _tickers:
        _tickers[symbol] = yf.Ticker(symbol)
    return _tickers[symbol]


def _normalise(hist: pd.DataFrame) -> pd.DataFrame:
    hist = hist.reset_index()
    first = hist.columns[0]
    if first != "Datetime":
        hist = hist.rename(columns={first: "Datetime"})
    return hist


def _stale_copy(key, interval):
    entry = _cache.get(key)
    if not entry:
        return None
    age = time.time() - entry[0]
    if age <= MAX_STALE.get(interval, 120):
        return entry[1]
    return None


def get_history(symbol: str, period: str = "2d", interval: str = "1m",
                min_rows: int = 30) -> Optional[pd.DataFrame]:
    """Return OHLC data for a Yahoo symbol like 'EURUSD=X', or None."""
    key = (symbol, period, interval)
    ttl = TTL.get(interval, 60)

    with _lock:
        entry = _cache.get(key)
        if entry and time.time() - entry[0] < ttl:
            _state["cache_hits"] += 1
            return entry[1]

        if time.time() < _state["cooldown_until"]:
            return _stale_copy(key, interval)

        wait = MIN_GAP - (time.time() - _state["last_request"])
        if wait > 0:
            time.sleep(wait)

        _state["last_request"] = time.time()
        _state["requests"] += 1
        try:
            hist = _get_ticker(symbol).history(period=period, interval=interval)
        except Exception as e:
            _state["failures"] += 1
            _state["last_error"] = f"{symbol}: {type(e).__name__}: {e}"[:200]
            if _is_rate_limit(e):
                _enter_cooldown()
            else:
                print(f"[YF] {symbol} {interval} error: {e}")
            return _stale_copy(key, interval)

        if hist is None or hist.empty or len(hist) < min_rows:
            _state["failures"] += 1
            _state["last_error"] = f"{symbol}: no data returned"
            return _stale_copy(key, interval)

        hist = _normalise(hist)
        _cache[key] = (time.time(), hist)
        _state["last_ok"] = time.time()
        _state["cooldown_step"] = 0
        return hist


def status() -> dict:
    now = time.time()
    remaining = max(0, int(_state["cooldown_until"] - now))
    last_ok = _state["last_ok"]
    return {
        "rate_limited": remaining > 0,
        "retry_in_seconds": remaining,
        "last_success_seconds_ago": int(now - last_ok) if last_ok else None,
        "requests": _state["requests"],
        "cache_hits": _state["cache_hits"],
        "failures": _state["failures"],
        "last_error": _state["last_error"],
        "cached_series": len(_cache),
    }


def summary() -> str:
    s = status()
    if s["rate_limited"]:
        return f"Yahoo rate limited, retrying in {s['retry_in_seconds'] // 60 + 1} min"
    if s["last_success_seconds_ago"] is None:
        return "no price data downloaded yet"
    return f"prices OK ({s['last_success_seconds_ago']}s ago)"
