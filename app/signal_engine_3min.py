"""
3-Minute Bot signal engine
Adapted from the original volatility signal bot script.
Uses Twelve Data. Includes session quality, choppiness, volatility detection,
expiry 2-5 min, protections, and supports 2 martingale levels.
"""
import datetime
import pandas as pd
import pandas_ta_classic as ta
import pytz
from typing import Dict, List, Optional, Tuple
from .data_source import TwelveDataClient
from .config import TWELVE_DATA_API_KEY

WAT = pytz.timezone("Africa/Lagos")

PAIRS = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY",
    "AUD/USD": "AUD/USD", "AUD/JPY": "AUD/JPY", "USD/CAD": "USD/CAD",
    "EUR/JPY": "EUR/JPY", "GBP/JPY": "GBP/JPY", "CHF/JPY": "CHF/JPY",
    "GBP/AUD": "GBP/AUD", "CAD/CHF": "CAD/CHF", "USD/CHF": "USD/CHF",
    "CAD/JPY": "CAD/JPY", "AUD/CHF": "AUD/CHF", "EUR/GBP": "EUR/GBP",
    "GBP/CAD": "GBP/CAD", "AUD/CAD": "AUD/CAD",
}

VOLATILITY_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY"]

class SignalEngine3Min:
    def __init__(self):
        self.client = TwelveDataClient(TWELVE_DATA_API_KEY)
        self.blacklisted_pairs = {}
        self.win_cooldown_pairs = {}
        self.skipped_pairs = {}
        self.consecutive_losses = 0
        self.high_volatility_mode = False
        self.last_volatility_check = None

    def get_session_quality(self):
        now_wat = datetime.datetime.now(WAT)
        hour = now_wat.hour
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
        if self.high_volatility_mode:
            return 5 if quality == "EXCELLENT" else 999
        if quality == "EXCELLENT": return 5
        if quality == "GOOD": return 5
        return 7

    def pick_expiry(self, adx_val: float, strength: str, conditions: int) -> int:
        # Always between 2 and 5 minutes
        if adx_val >= 35 and strength == "STRONG" and conditions >= 6:   return 2
        elif adx_val >= 30 and strength == "STRONG" and conditions >= 5: return 2
        elif adx_val >= 25 and strength in ["STRONG", "MODERATE"] and conditions >= 4: return 3
        elif adx_val >= 20 and conditions >= 3: return 4
        else: return 5

    def is_market_choppy(self, hist: pd.DataFrame) -> Tuple[bool, List[str]]:
        choppy_count = 0
        reasons = []
        try:
            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            atr = ta.atr(high, low, close, length=14)
            if atr is not None and len(atr) > 2:
                curr_atr = atr.iloc[-2]
                avg_atr = atr.iloc[-15:-2].mean()
                if avg_atr > 0 and curr_atr < avg_atr * 0.6:
                    choppy_count += 1
                    reasons.append("ATR too low")
            bb = ta.bbands(close, length=20, std=2)
            if bb is not None:
                bb_cols = bb.columns.tolist()
                bbu = [c for c in bb_cols if "BBU" in c]
                bbl = [c for c in bb_cols if "BBL" in c]
                bbm = [c for c in bb_cols if "BBM" in c]
                if bbu and bbl and bbm:
                    bb_width = (bb[bbu[0]].iloc[-2] - bb[bbl[0]].iloc[-2]) / bb[bbm[0]].iloc[-2]
                    avg_bb = ((bb[bbu[0]] - bb[bbl[0]]) / bb[bbm[0]]).iloc[-15:-2].mean()
                    if avg_bb > 0 and bb_width < avg_bb * 0.5:
                        choppy_count += 1
                        reasons.append("BB bands too narrow")
            closes = close.iloc[-8:-1].values
            directions = []
            for j in range(1, len(closes)):
                if closes[j] > closes[j-1]: directions.append(1)
                elif closes[j] < closes[j-1]: directions.append(-1)
                else: directions.append(0)
            changes = sum(1 for j in range(1, len(directions)) if directions[j] != 0 and directions[j-1] != 0 and directions[j] != directions[j-1])
            if changes >= 4:
                choppy_count += 1
                reasons.append(f"Zigzagging - {changes} changes")
        except Exception as e:
            print(f"Choppiness error: {e}")
            return False, []
        return choppy_count >= 2, reasons

    def check_pair_volatility(self, symbol: str) -> bool:
        try:
            hist = self.client.get_time_series(symbol, "1min", 60)
            if hist is None or len(hist) < 30:
                return False
            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            vol_count = 0
            atr = ta.atr(high, low, close, length=14)
            if atr is not None and len(atr) > 20:
                curr_atr = atr.iloc[-2]
                avg_atr = atr.iloc[-20:-2].mean()
                if avg_atr > 0 and curr_atr / avg_atr > 1.8:
                    vol_count += 1
            recent_ranges = (high - low).iloc[-10:-1]
            avg_range = recent_ranges.mean()
            last_range = (high - low).iloc[-2]
            if avg_range > 0 and last_range > avg_range * 2.5:
                vol_count += 1
            avg_move = abs(close.diff().iloc[-20:-1]).mean()
            big_moves = sum(1 for j in range(1, 8) if abs(close.iloc[-j] - close.iloc[-j-1]) > avg_move * 2)
            if big_moves >= 4:
                vol_count += 1
            return vol_count >= 2
        except Exception:
            return False

    def detect_market_volatility(self) -> Tuple[bool, str]:
        volatile_count = 0
        volatile_pairs = []
        for pair in VOLATILITY_PAIRS:
            if self.check_pair_volatility(PAIRS.get(pair, pair)):
                volatile_count += 1
                volatile_pairs.append(pair)
        if volatile_count >= 2:
            return True, f"{', '.join(volatile_pairs)} showing high volatility"
        return False, ""

    def check_volatility(self):
        now = datetime.datetime.now()
        if self.last_volatility_check and (now - self.last_volatility_check).seconds < 15 * 60:
            return
        self.last_volatility_check = now
        is_volatile, reason = self.detect_market_volatility()
        if is_volatile and not self.high_volatility_mode:
            self.high_volatility_mode = True
            print(f"HIGH VOLATILITY: {reason}")
        elif not is_volatile and self.high_volatility_mode:
            self.high_volatility_mode = False
            print("Volatility normalised")

    def get_forex_data(self, quality: str) -> Dict:
        rates = {}
        min_conds = self.get_min_conditions(quality)
        if self.high_volatility_mode and quality == "GOOD":
            print("High volatility - GOOD session blocked")
            return rates
        now = datetime.datetime.now()

        for d in [self.blacklisted_pairs, self.win_cooldown_pairs, self.skipped_pairs]:
            expired = [p for p, t in d.items() if now >= t]
            for p in expired:
                del d[p]

        for pair_name, symbol in PAIRS.items():
            if pair_name in self.blacklisted_pairs or pair_name in self.win_cooldown_pairs or pair_name in self.skipped_pairs:
                continue
            try:
                hist = self.client.get_time_series(symbol, "1min", 150)
                if hist is None or len(hist) < 120:
                    continue
                close = hist["Close"]
                high = hist["High"]
                low = hist["Low"]
                choppy, _ = self.is_market_choppy(hist)
                if choppy:
                    continue

                ma2 = ta.sma(close, length=2)
                ma5 = ta.sma(close, length=5)
                ma100 = ta.sma(close, length=100)
                if ma2 is None or ma5 is None or len(ma2) < 3:
                    continue

                i = -2
                curr_ma2 = ma2.iloc[i]
                curr_ma5 = ma5.iloc[i]
                curr_ma100 = ma100.iloc[i] if ma100 is not None else curr_ma2
                curr_price = close.iloc[i]

                buy_conditions = 0
                sell_conditions = 0
                buy_reasons = []
                sell_reasons = []

                prev_ma2 = ma2.iloc[i-1]
                prev_ma5 = ma5.iloc[i-1]
                if prev_ma2 <= prev_ma5 and curr_ma2 > curr_ma5:
                    buy_conditions += 1
                    buy_reasons.append("MA2 crossed above MA5")
                if prev_ma2 >= prev_ma5 and curr_ma2 < curr_ma5:
                    sell_conditions += 1
                    sell_reasons.append("MA2 crossed below MA5")
                if curr_ma2 > curr_ma5:
                    buy_conditions += 1
                    buy_reasons.append("MA2 above MA5")
                if curr_ma2 < curr_ma5:
                    sell_conditions += 1
                    sell_reasons.append("MA2 below MA5")

                adx_data = ta.adx(high, low, close, length=14)
                adx_val = 0
                if adx_data is not None:
                    adx_col = [c for c in adx_data.columns if "ADX" in c and "DM" not in c]
                    if adx_col:
                        adx_val = adx_data[adx_col[0]].iloc[i]

                if adx_val < 20:
                    continue

                trend = "UPTREND" if curr_ma2 > curr_ma5 > curr_ma100 else "DOWNTREND" if curr_ma2 < curr_ma5 < curr_ma100 else "RANGING"
                strength = "STRONG" if adx_val >= 30 else "MODERATE" if adx_val >= 20 else "WEAK"
                if trend == "RANGING" and strength == "WEAK":
                    continue

                expiry = self.pick_expiry(adx_val, strength, max(buy_conditions, sell_conditions))

                if buy_conditions >= min_conds:
                    rates[pair_name] = {
                        "signal": "BUY", "conditions": buy_conditions, "reasons": buy_reasons,
                        "price": round(curr_price, 5), "adx": round(adx_val, 1),
                        "trend": trend, "strength": strength, "expiry_mins": expiry
                    }
                elif sell_conditions >= min_conds:
                    rates[pair_name] = {
                        "signal": "SELL", "conditions": sell_conditions, "reasons": sell_reasons,
                        "price": round(curr_price, 5), "adx": round(adx_val, 1),
                        "trend": trend, "strength": strength, "expiry_mins": expiry
                    }
            except Exception as e:
                print(f"Error on {pair_name}: {e}")
                continue
        return rates
