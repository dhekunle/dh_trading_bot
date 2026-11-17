"""
Shared signal engine used by the Patience Bot and the 3 min Bot.

This is the full logic from the two original scripts: session quality,
choppiness filter, nine scoring conditions, M5 and M15 confirmation, news
filter, Groq confirmation, and the loss/win/skip protections.
"""
import datetime
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytz
import requests

from . import indicators as ind
from . import yf_data

try:
    from groq import Groq
except Exception:  # groq not installed
    Groq = None

WAT = pytz.timezone("Africa/Lagos")

PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X", "AUD/JPY": "AUDJPY=X", "USD/CAD": "USDCAD=X",
    "EUR/JPY": "EURJPY=X", "GBP/JPY": "GBPJPY=X", "CHF/JPY": "CHFJPY=X",
    "GBP/AUD": "GBPAUD=X", "CAD/CHF": "CADCHF=X", "USD/CHF": "USDCHF=X",
    "CAD/JPY": "CADJPY=X", "AUD/CHF": "AUDCHF=X", "EUR/GBP": "EURGBP=X",
    "GBP/CAD": "GBPCAD=X", "AUD/CAD": "AUDCAD=X",
}

# Protection settings (same as the original scripts)
MAX_CONSECUTIVE_LOSS = 2
COOLDOWN_MINUTES = 5
BLACKLIST_MINUTES = 30
WIN_COOLDOWN_MINUTES = 15
SKIP_BAN_MINUTES = 20

# Price data older than this is treated as a closed market
MAX_DATA_AGE_SECONDS = 600
GROQ_RETRY_MINUTES = 10

# ---------------------------------------------------------------- news filter
_news_cache = {"at": 0.0, "events": []}
_news_lock = threading.Lock()


def check_forex_news() -> List[dict]:
    """High impact news within -15 to +30 minutes. Cached for 5 minutes."""
    with _news_lock:
        if time.time() - _news_cache["at"] < 300:
            events = _news_cache["events"]
        else:
            events = None
            try:
                r = requests.get(
                    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                    headers={"User-Agent": "Mozilla/5.0"}, timeout=5,
                )
                if r.status_code == 200:
                    events = r.json()
            except Exception as e:
                print(f"[NEWS] {e}")
            _news_cache["at"] = time.time()
            if events is not None:
                _news_cache["events"] = events
            else:
                events = _news_cache["events"]

    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    high_news = []
    for event in events or []:
        try:
            if event.get("impact", "").lower() != "high":
                continue
            date_str = event.get("date", "")
            if not date_str:
                continue
            event_time = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
            event_utc = event_time.astimezone(pytz.utc).replace(tzinfo=None)
            diff_mins = (event_utc - now_utc).total_seconds() / 60
            if -15 <= diff_mins <= 30:
                high_news.append({
                    "title": event.get("title", "Unknown"),
                    "country": event.get("country", ""),
                    "time_wat": event_time.astimezone(WAT),
                    "time_str": event_time.astimezone(WAT).strftime("%I:%M %p WAT"),
                    "diff": round(diff_mins),
                })
        except Exception:
            continue
    return high_news


def news_status() -> Tuple[bool, List[dict], Optional[datetime.datetime]]:
    """Returns (safe_to_trade, news_list, safe_after_time)."""
    news = check_forex_news()
    if not news:
        return True, [], None
    return False, news, max(n["time_wat"] for n in news) + datetime.timedelta(minutes=15)


# ------------------------------------------------------------------ the engine
class BaseEngine:
    name = "Bot"
    volatility_enabled = False

    def __init__(self, groq_api_key: str = ""):
        self.blacklisted_pairs = {}
        self.win_cooldown_pairs = {}
        self.skipped_pairs = {}
        self.consecutive_losses = 0
        self.cooldown_until = None
        self.high_volatility_mode = False

        self.groq_client = None
        if groq_api_key and Groq is not None:
            try:
                self.groq_client = Groq(api_key=groq_api_key, timeout=30.0, max_retries=1)
            except Exception as e:
                print(f"[{self.name}] Groq setup failed: {e}")
        self.groq_blocked_until = None
        self.groq_notified_at = None

        self.notifier = None          # callable(text) -> private Telegram message
        self.group_notifier = None    # callable(text) -> Telegram group message

        self.last_scan_info = "Waiting for first scan"
        self.last_scan_at = None
        self.scan_counts = {"total": 0, "with_data": 0, "stale": 0, "skipped": 0}

    # ------------------------------------------------------------- helpers
    def _notify(self, text: str):
        if self.notifier:
            try:
                self.notifier(text)
            except Exception as e:
                print(f"[{self.name}] notify error: {e}")

    def _notify_group(self, text: str):
        if self.group_notifier:
            try:
                self.group_notifier(text)
            except Exception as e:
                print(f"[{self.name}] group notify error: {e}")

    def set_info(self, text: str):
        self.last_scan_info = text
        self.last_scan_at = datetime.datetime.now(WAT)

    @property
    def groq_configured(self) -> bool:
        return self.groq_client is not None

    # ------------------------------------------------------------- sessions
    def get_session_quality(self):
        hour = datetime.datetime.now(WAT).hour
        sessions = []
        if 1 <= hour < 9:   sessions.append("Tokyo")
        if 9 <= hour < 17:  sessions.append("London")
        if 14 <= hour < 22: sessions.append("New York")
        if 14 <= hour < 17: sessions.append("London/NY Overlap")
        if not sessions:
            return None, "CLOSED", "Market is closed"
        if 2 <= hour < 5:   return sessions, "EXCELLENT", "Tokyo peak hours"
        if 9 <= hour < 12:  return sessions, "EXCELLENT", "Early London - highest accuracy"
        if 14 <= hour < 17: return sessions, "GOOD", "London/NY Overlap - volatile"
        if 5 <= hour < 9:   return sessions, "GOOD", "Late Tokyo"
        if 12 <= hour < 14: return sessions, "GOOD", "Mid London"
        if 17 <= hour < 22: return sessions, "AVOID", "NY only - choppy"
        return sessions, "AVOID", "Low quality session"

    def get_min_conditions(self, quality: str) -> int:
        if quality in ("EXCELLENT", "GOOD"):
            return 5
        return 7

    def quality_blocked(self, quality: str) -> Optional[str]:
        """Return a reason string if this session quality must not be traded."""
        return None

    def check_volatility(self):
        """Overridden by the 3 min engine."""
        return

    def pick_expiry(self, adx_val, strength, conditions) -> int:
        if adx_val >= 35 and strength == "STRONG" and conditions >= 6:   return 2
        elif adx_val >= 30 and strength == "STRONG" and conditions >= 5: return 2
        elif adx_val >= 25 and strength in ["STRONG", "MODERATE"] and conditions >= 4: return 3
        elif adx_val >= 20 and conditions >= 3: return 4
        else: return 5

    # ------------------------------------------------------------- filters
    def is_market_choppy(self, close, high, low) -> Tuple[bool, List[str]]:
        choppy_count = 0
        reasons = []
        try:
            atr = ind.atr(high, low, close, 14)
            if atr is not None and len(atr) > 2:
                curr_atr = atr.iloc[-2]
                avg_atr = atr.iloc[-15:-2].mean()
                if avg_atr > 0 and curr_atr < avg_atr * 0.6:
                    choppy_count += 1
                    reasons.append("ATR too low")
            upper, mid, lower = ind.bbands(close, 20, 2)
            width = (upper - lower) / mid
            bb_width = width.iloc[-2]
            avg_bb_width = width.iloc[-15:-2].mean()
            if avg_bb_width > 0 and bb_width < avg_bb_width * 0.5:
                choppy_count += 1
                reasons.append("BB bands too narrow")
            closes = close.iloc[-8:-1].values
            directions = []
            for j in range(1, len(closes)):
                if closes[j] > closes[j - 1]:   directions.append(1)
                elif closes[j] < closes[j - 1]: directions.append(-1)
                else:                           directions.append(0)
            changes = 0
            for j in range(1, len(directions)):
                if directions[j] != 0 and directions[j - 1] != 0 and directions[j] != directions[j - 1]:
                    changes += 1
            if changes >= 4:
                choppy_count += 1
                reasons.append(f"Zigzagging - {changes} changes")
        except Exception as e:
            print(f"[{self.name}] choppiness error: {e}")
            return False, []
        return choppy_count >= 2, reasons

    def detect_candle_patterns(self, hist: pd.DataFrame):
        patterns = []
        try:
            o = hist["Open"].values; h = hist["High"].values
            l = hist["Low"].values;  c = hist["Close"].values
            i = -2
            body = abs(c[i] - o[i])
            wick_up = h[i] - max(c[i], o[i])
            wick_down = min(c[i], o[i]) - l[i]
            is_bull = c[i] > o[i]
            is_bear = c[i] < o[i]
            prev_body = abs(c[i - 1] - o[i - 1])
            prev_is_bull = c[i - 1] > o[i - 1]
            prev_is_bear = c[i - 1] < o[i - 1]
            if wick_down > body * 2 and wick_up < body * 0.5 and is_bull:
                patterns.append(("BULLISH", "Hammer"))
            if is_bull and prev_is_bear and c[i] > o[i - 1] and o[i] < c[i - 1] and body > prev_body:
                patterns.append(("BULLISH", "Bullish Engulfing"))
            if c[i - 2] < o[i - 2] and abs(c[i - 1] - o[i - 1]) < prev_body * 0.3 and c[i] > o[i] and c[i] > (o[i - 2] + c[i - 2]) / 2:
                patterns.append(("BULLISH", "Morning Star"))
            if wick_down > body * 3 and is_bull:
                patterns.append(("BULLISH", "Bullish Pin Bar"))
            if wick_up > body * 2 and wick_down < body * 0.5 and is_bear:
                patterns.append(("BEARISH", "Shooting Star"))
            if is_bear and prev_is_bull and c[i] < o[i - 1] and o[i] > c[i - 1] and body > prev_body:
                patterns.append(("BEARISH", "Bearish Engulfing"))
            if c[i - 2] > o[i - 2] and abs(c[i - 1] - o[i - 1]) < prev_body * 0.3 and c[i] < o[i] and c[i] < (o[i - 2] + c[i - 2]) / 2:
                patterns.append(("BEARISH", "Evening Star"))
            if wick_up > body * 3 and is_bear:
                patterns.append(("BEARISH", "Bearish Pin Bar"))
            if body < (h[i] - l[i]) * 0.1:
                patterns.append(("NEUTRAL", "Doji"))
        except Exception as e:
            print(f"[{self.name}] pattern error: {e}")
        return patterns

    def get_trend_strength(self, hist, ma2, ma5, ma100):
        try:
            i = -2
            curr_ma2 = ma2.iloc[i]; curr_ma5 = ma5.iloc[i]; curr_ma100 = ma100.iloc[i]
            adx_series = ind.adx(hist["High"], hist["Low"], hist["Close"], 14)
            adx_val = adx_series.iloc[i]
            if pd.isna(adx_val):
                adx_val = 0
            if curr_ma2 > curr_ma5 > curr_ma100:   trend = "UPTREND"
            elif curr_ma2 < curr_ma5 < curr_ma100: trend = "DOWNTREND"
            else:                                  trend = "RANGING"
            if trend == "RANGING":
                return trend, "WEAK", adx_val
            strength = "STRONG" if adx_val >= 30 else "MODERATE" if adx_val >= 20 else "WEAK"
            return trend, strength, adx_val
        except Exception as e:
            print(f"[{self.name}] trend error: {e}")
            return "UNKNOWN", "UNKNOWN", 0

    def _confirm_timeframe(self, symbol, direction, interval, fast, mid, slow, min_rows) -> bool:
        """M5 / M15 confirmation. Returns True when the data is missing (same as the originals)."""
        try:
            hist = yf_data.get_history(symbol, "5d", interval, min_rows=min_rows)
            if hist is None or len(hist) < min_rows:
                return True
            close = hist["Close"]
            ma_fast = ind.sma(close, fast).iloc[-2]
            ma_mid = ind.sma(close, mid).iloc[-2]
            ma_slow = ind.sma(close, slow).iloc[-2]
            rsi_val = ind.rsi(close, 14).iloc[-2]
            if pd.isna(rsi_val):
                rsi_val = 50
            price = close.iloc[-2]
            if any(pd.isna(v) for v in (ma_fast, ma_mid, ma_slow, price)):
                return True
            bullish = ma_fast > ma_mid and price > ma_slow and rsi_val > 45
            bearish = ma_fast < ma_mid and price < ma_slow and rsi_val < 55
            if direction == "BUY":
                return not bearish if not bullish else True
            return not bullish if not bearish else True
        except Exception as e:
            print(f"[{self.name}] {interval} confirm error: {e}")
            return True

    def confirm_m5(self, symbol, direction):
        return self._confirm_timeframe(symbol, direction, "5m", 2, 5, 20, 30)

    def confirm_m15(self, symbol, direction):
        return self._confirm_timeframe(symbol, direction, "15m", 5, 10, 20, 20)

    # ------------------------------------------------------------- scoring
    def analyze_pair(self, pair_name: str, symbol: str, min_conds: int):
        """Returns (result_dict | None, status) where status is data / stale / filtered."""
        hist = yf_data.get_history(symbol, "2d", "1m", min_rows=120)
        if hist is None or len(hist) < 120:
            return None, "nodata"

        last_ts = pd.Timestamp(hist["Datetime"].iloc[-1])
        if last_ts.tzinfo is None:
            last_ts = last_ts.tz_localize("UTC")
        age = (pd.Timestamp.now(tz="UTC") - last_ts.tz_convert("UTC")).total_seconds()
        if age > MAX_DATA_AGE_SECONDS:
            return None, "stale"

        close = hist["Close"]; high = hist["High"]; low = hist["Low"]

        choppy, _ = self.is_market_choppy(close, high, low)
        if choppy:
            return None, "filtered"

        ma2 = ind.sma(close, 2); ma5 = ind.sma(close, 5); ma100 = ind.sma(close, 100)
        bb_upper, _, bb_lower = ind.bbands(close, 20, 2)
        stoch_k, stoch_d = ind.stoch(high, low, close, 5, 3, 3)
        rsi = ind.rsi(close, 14)

        values = [ma2.iloc[-3], ma2.iloc[-2], ma5.iloc[-3], ma5.iloc[-2], ma100.iloc[-2],
                  close.iloc[-2], bb_upper.iloc[-2], bb_lower.iloc[-2],
                  stoch_k.iloc[-2], stoch_d.iloc[-2], stoch_k.iloc[-3]]
        if any(pd.isna(v) for v in values):
            return None, "filtered"

        prev_ma2 = round(float(ma2.iloc[-3]), 5); curr_ma2 = round(float(ma2.iloc[-2]), 5)
        prev_ma5 = round(float(ma5.iloc[-3]), 5); curr_ma5 = round(float(ma5.iloc[-2]), 5)
        curr_ma100 = round(float(ma100.iloc[-2]), 5)
        curr_price = round(float(close.iloc[-2]), 5)
        curr_upper = round(float(bb_upper.iloc[-2]), 5)
        curr_lower = round(float(bb_lower.iloc[-2]), 5)
        curr_k = round(float(stoch_k.iloc[-2]), 2)
        curr_d = round(float(stoch_d.iloc[-2]), 2)
        prev_k = round(float(stoch_k.iloc[-3]), 2)
        curr_rsi = round(float(rsi.iloc[-2]), 2) if not pd.isna(rsi.iloc[-2]) else 50.0

        patterns = self.detect_candle_patterns(hist)
        bullish_patterns = [p[1] for p in patterns if p[0] == "BULLISH"]
        bearish_patterns = [p[1] for p in patterns if p[0] == "BEARISH"]
        neutral_patterns = [p[1] for p in patterns if p[0] == "NEUTRAL"]

        trend, strength, adx_val = self.get_trend_strength(hist, ma2, ma5, ma100)
        adx_val = float(adx_val)
        if trend == "RANGING" and strength == "WEAK":
            return None, "filtered"
        if neutral_patterns:
            return None, "filtered"
        if adx_val < 20:
            return None, "filtered"

        bullish_cross = prev_ma2 <= prev_ma5 and curr_ma2 > curr_ma5
        bearish_cross = prev_ma2 >= prev_ma5 and curr_ma2 < curr_ma5
        bb_range = (curr_upper - curr_lower) * 0.15

        buy = 0; sell = 0
        buy_reasons = []; sell_reasons = []

        if bullish_cross: buy += 1;  buy_reasons.append("MA2 crossed above MA5")
        if bearish_cross: sell += 1; sell_reasons.append("MA2 crossed below MA5")
        if curr_ma2 > curr_ma5: buy += 1;  buy_reasons.append("MA2 above MA5")
        if curr_ma2 < curr_ma5: sell += 1; sell_reasons.append("MA2 below MA5")
        if curr_price <= curr_lower + bb_range: buy += 1;  buy_reasons.append("Price near lower BB")
        if curr_price >= curr_upper - bb_range: sell += 1; sell_reasons.append("Price near upper BB")
        if curr_k < 20 and curr_k > prev_k: buy += 1;  buy_reasons.append(f"Stochastic oversold ({curr_k})")
        if curr_k > 80 and curr_k < prev_k: sell += 1; sell_reasons.append(f"Stochastic overbought ({curr_k})")
        if curr_price > curr_ma100: buy += 1;  buy_reasons.append("Price above MA100")
        if curr_price < curr_ma100: sell += 1; sell_reasons.append("Price below MA100")
        if curr_rsi < 35:
            buy += 1; buy_reasons.append(f"RSI oversold ({curr_rsi})")
        elif 45 < curr_rsi < 60:
            buy += 1; buy_reasons.append(f"RSI bullish zone ({curr_rsi})")
        if curr_rsi > 65:
            sell += 1; sell_reasons.append(f"RSI overbought ({curr_rsi})")
        elif 40 < curr_rsi < 55:
            sell += 1; sell_reasons.append(f"RSI bearish zone ({curr_rsi})")
        if bullish_patterns: buy += 1;  buy_reasons.append(f"Pattern: {', '.join(bullish_patterns)}")
        if bearish_patterns: sell += 1; sell_reasons.append(f"Pattern: {', '.join(bearish_patterns)}")
        if trend == "UPTREND" and strength == "STRONG":   buy += 1;  buy_reasons.append("Strong uptrend confirmed")
        if trend == "DOWNTREND" and strength == "STRONG": sell += 1; sell_reasons.append("Strong downtrend confirmed")

        expiry = self.pick_expiry(adx_val, strength, buy if buy >= min_conds else sell)

        def build(direction, conditions, reasons, patterns_list):
            if not self.confirm_m5(symbol, direction):
                return None
            if not self.confirm_m15(symbol, direction):
                return None
            reasons = reasons + [f"M5 + M15 confirms {direction}"]
            return {
                "signal": direction, "conditions": int(conditions), "reasons": reasons,
                "price": curr_price, "stoch_k": curr_k, "stoch_d": curr_d,
                "rsi": curr_rsi, "bb_upper": curr_upper, "bb_lower": curr_lower,
                "ma2": curr_ma2, "ma5": curr_ma5, "ma100": curr_ma100,
                "trend": trend, "strength": strength, "adx": round(adx_val, 1),
                "patterns": patterns_list, "expiry_mins": int(expiry),
            }

        if buy >= min_conds:
            return build("BUY", buy, buy_reasons, bullish_patterns), "filtered"
        if sell >= min_conds:
            return build("SELL", sell, sell_reasons, bearish_patterns), "filtered"
        return None, "filtered"

    def _expire_lists(self):
        now = datetime.datetime.now()
        for d in (self.blacklisted_pairs, self.win_cooldown_pairs, self.skipped_pairs):
            for pair in [p for p, t in d.items() if now >= t]:
                del d[pair]

    def get_forex_data(self, quality: str) -> Dict:
        rates = {}
        self.scan_counts = {"total": 0, "with_data": 0, "stale": 0, "skipped": 0}
        reason = self.quality_blocked(quality)
        if reason:
            print(f"[{self.name}] {reason}")
            return rates

        min_conds = self.get_min_conditions(quality)
        self._expire_lists()

        for pair_name, symbol in PAIRS.items():
            if (pair_name in self.blacklisted_pairs or pair_name in self.win_cooldown_pairs
                    or pair_name in self.skipped_pairs):
                self.scan_counts["skipped"] += 1
                continue
            self.scan_counts["total"] += 1
            try:
                result, status = self.analyze_pair(pair_name, symbol, min_conds)
            except Exception as e:
                print(f"[{self.name}] error on {pair_name}: {e}")
                continue
            if status == "nodata":
                continue
            if status == "stale":
                self.scan_counts["stale"] += 1
                continue
            self.scan_counts["with_data"] += 1
            if result:
                rates[pair_name] = result
        return rates

    # ---------------------------------------------------------------- Groq
    def build_prompt(self, rates, sessions, quality) -> str:
        pairs_text = ""
        for pair, d in rates.items():
            reasons_text = "\n    ".join(d["reasons"])
            patterns_text = ", ".join(d["patterns"]) if d["patterns"] else "None"
            pairs_text += (
                f"  {pair}:\n    Signal: {d['signal']}\n    Conditions Met: {d['conditions']}\n"
                f"    Price: {d['price']}\n    RSI: {d['rsi']}\n    ADX: {d['adx']}\n"
                f"    Suggested Expiry: {d['expiry_mins']} min\n"
                f"    MA2: {d['ma2']} | MA5: {d['ma5']} | MA100: {d['ma100']}\n"
                f"    BB Upper: {d['bb_upper']} | BB Lower: {d['bb_lower']}\n"
                f"    Stochastic K: {d['stoch_k']} | D: {d['stoch_d']}\n"
                f"    Trend: {d['trend']} | Strength: {d['strength']}\n"
                f"    Candle Patterns: {patterns_text}\n    Reasons:\n    {reasons_text}\n\n"
            )
        session_text = ", ".join(sessions)
        market_line = ""
        adx_rule = "1. ADX must be above 25"
        last_rule = "6. If not 100% sure - output HOLD"
        if self.volatility_enabled:
            note = ("HIGH VOLATILITY - be extra strict, reject anything uncertain"
                    if self.high_volatility_mode else "Normal market conditions")
            market_line = f"Market Mode: {note}\n"
            adx_rule = "1. ADX must be above 25 (above 30 during high volatility)"
            last_rule = ("6. During HIGH VOLATILITY - reject anything not perfectly aligned\n"
                         "7. If not 100% sure - output HOLD")
        return f"""
You are a VERY STRICT and CONSERVATIVE binary options analyst.
All pairs below passed M1 + M5 + M15 + choppiness filter.

Current Sessions: {session_text}
Session Quality: {quality}
{market_line}
Pairs passed all filters:
{pairs_text}

STRICT RULES:
{adx_rule}
2. Candle pattern must confirm direction
3. RSI must clearly confirm (below 40 BUY, above 60 SELL)
4. MA cross must be present for HIGH confidence
5. Choose best expiry 2-5 mins:
   - ADX 35+ STRONG = 2 min
   - ADX 30+ STRONG = 2 min
   - ADX 25+ MODERATE = 3 min
   - ADX 20+ = 4 min
   - Weak = 5 min
{last_rule}

Respond ONLY in this exact format:
\u25cf Asset: [pair name]
\u25cf Action: BUY (Call) or SELL (Put)
\u25cf Expiry: [2, 3, 4, or 5] Minutes
\u25cf Confidence: High or Medium
"""

    def ask_groq(self, rates, sessions, quality) -> Optional[str]:
        if not self.groq_client:
            return None
        now = datetime.datetime.now()
        if self.groq_blocked_until and now < self.groq_blocked_until:
            return None
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": self.build_prompt(rates, sessions, quality)}],
                reasoning_effort="low",
                max_completion_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            text = str(e).lower()
            if any(x in text for x in ["rate_limit", "429", "quota", "exceeded", "limit"]):
                self.groq_blocked_until = now + datetime.timedelta(minutes=GROQ_RETRY_MINUTES)
                if not self.groq_notified_at or (now - self.groq_notified_at).total_seconds() > 3600:
                    self.groq_notified_at = now
                    self._notify(
                        f"{self.name}: GROQ LIMIT REACHED!\n"
                        f"{datetime.datetime.now(WAT).strftime('%I:%M %p WAT')}\n\n"
                        f"Signals are paused. Will retry automatically in {GROQ_RETRY_MINUTES} mins.\n"
                        f"If it stays blocked, replace the Groq key in Render."
                    )
            else:
                print(f"[{self.name}] Groq error: {e}")
            return None

    @staticmethod
    def extract_action(response: Optional[str]):
        if not response:
            return None, None, 5, None
        asset = action = confidence = None
        expiry = 5
        for line in response.split("\n"):
            if "Asset:" in line:  asset = line.split("Asset:")[-1].strip()
            if "Action:" in line: action = line.split("Action:")[-1].strip()
            if "Confidence:" in line: confidence = line.split("Confidence:")[-1].strip()
            if "Expiry:" in line:
                try:
                    text = line.split("Expiry:")[-1].strip()
                    expiry = int("".join(filter(str.isdigit, text.split()[0])))
                    expiry = max(2, min(5, expiry))
                except Exception:
                    expiry = 5
        return asset, action, expiry, confidence

    def get_confirmed_signal(self, rates, sessions, quality):
        """Returns (asset, direction, groq_response, expiry) or (None, None, None, 5)."""
        none = (None, None, None, 5)
        if not self.groq_client:
            print(f"[{self.name}] Groq key missing - no signals can be confirmed")
            return none
        if self.groq_blocked_until and datetime.datetime.now() < self.groq_blocked_until:
            print(f"[{self.name}] Groq limit active - waiting")
            return none

        print(f"[{self.name}] Asking Groq about {len(rates)} setup(s)...")
        response = self.ask_groq(rates, sessions, quality)
        print(f"[{self.name}] Groq: {response}")
        if not response:
            return none
        if "HOLD" in response.upper():
            return none

        asset_text, action_text, expiry, confidence = self.extract_action(response)
        confidence_text = (confidence or response).upper()
        if "HIGH" not in confidence_text:
            return none
        if not asset_text or not action_text:
            return none

        asset = next((p for p in rates if p == asset_text), None)
        if asset is None:
            asset = next((p for p in rates if p in asset_text), None)
        if asset is None:
            print(f"[{self.name}] Groq picked unknown pair: {asset_text}")
            return none

        direction = "BUY" if "BUY" in action_text.upper() else "SELL"
        if direction != rates[asset]["signal"]:
            print(f"[{self.name}] Groq direction does not match the setup - rejected")
            return none
        return asset, direction, response, expiry

    # ---------------------------------------------------------- protections
    def cooldown_remaining(self) -> int:
        if self.cooldown_until:
            left = (self.cooldown_until - datetime.datetime.now()).total_seconds()
            if left > 0:
                return int(left)
            self.cooldown_until = None
        return 0

    def skip_pair(self, asset: str):
        self.skipped_pairs[asset] = datetime.datetime.now() + datetime.timedelta(minutes=SKIP_BAN_MINUTES)

    def register_result(self, asset: str, result: str) -> Optional[str]:
        """Update protections after a result. Returns a group message if a cooldown starts."""
        now = datetime.datetime.now()
        result = (result or "").upper()
        if result == "WIN":
            self.consecutive_losses = 0
            self.win_cooldown_pairs[asset] = now + datetime.timedelta(minutes=WIN_COOLDOWN_MINUTES)
        elif result == "LOSS":
            self.consecutive_losses += 1
            self.blacklisted_pairs[asset] = now + datetime.timedelta(minutes=BLACKLIST_MINUTES)
            if self.consecutive_losses >= MAX_CONSECUTIVE_LOSS:
                count = self.consecutive_losses
                self.cooldown_until = now + datetime.timedelta(minutes=COOLDOWN_MINUTES)
                self.consecutive_losses = 0
                return f"{count} CONSECUTIVE LOSSES!\nBot paused {COOLDOWN_MINUTES} mins!"
        else:
            self.consecutive_losses = 0
        return None
