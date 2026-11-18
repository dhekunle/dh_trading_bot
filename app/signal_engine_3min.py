"""
3 min Bot engine (the original Volatility Signal Bot logic).
Adds high volatility detection on top of the shared engine.
"""
import datetime
from typing import Optional, Tuple

from . import indicators as ind
from . import yf_data
from .config import GROQ_API_KEY, GROQ_API_KEY_3MIN
from .engine_core import BaseEngine, PAIRS, WAT  # noqa: F401  (re-exported)

VOLATILITY_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
}
VOLATILITY_CHECK_MINS = 15


class SignalEngine3Min(BaseEngine):
    name = "3 min Bot"
    volatility_enabled = True

    def __init__(self):
        super().__init__(GROQ_API_KEY_3MIN or GROQ_API_KEY)
        self.last_volatility_check = None

    NORMAL_MIN_CONDITIONS = 3      # was 5 in the original script
    STRICT_MIN_CONDITIONS = 5      # high volatility mode stays strict

    def get_min_conditions(self, quality: str) -> int:
        if self.high_volatility_mode:
            return self.STRICT_MIN_CONDITIONS if quality == "EXCELLENT" else 999
        if quality in ("EXCELLENT", "GOOD"):
            return self.NORMAL_MIN_CONDITIONS
        return 7

    def quality_blocked(self, quality: str) -> Optional[str]:
        if self.high_volatility_mode and quality == "GOOD":
            return "High volatility - GOOD session blocked"
        return None

    def check_pair_volatility(self, symbol: str) -> bool:
        try:
            # Same cached 2 day download the scan uses, so no extra requests
            hist = yf_data.get_history(symbol, "2d", "1m", min_rows=30)
            if hist is None or len(hist) < 30:
                return False
            close = hist["Close"]; high = hist["High"]; low = hist["Low"]
            vol_count = 0
            atr = ind.atr(high, low, close, 14)
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
            big_moves = sum(1 for j in range(1, 8)
                            if abs(close.iloc[-j] - close.iloc[-j - 1]) > avg_move * 2)
            if big_moves >= 4:
                vol_count += 1
            return vol_count >= 2
        except Exception as e:
            print(f"[{self.name}] pair volatility error: {e}")
            return False

    def detect_market_volatility(self) -> Tuple[bool, str]:
        volatile_pairs = []
        for pair_name, symbol in VOLATILITY_PAIRS.items():
            if self.check_pair_volatility(symbol):
                volatile_pairs.append(pair_name)
        if len(volatile_pairs) >= 2:
            return True, f"{', '.join(volatile_pairs)} showing high volatility"
        return False, ""

    def check_volatility(self):
        now = datetime.datetime.now()
        if self.last_volatility_check and \
                (now - self.last_volatility_check).total_seconds() < VOLATILITY_CHECK_MINS * 60:
            return
        self.last_volatility_check = now
        is_volatile, reason = self.detect_market_volatility()
        if is_volatile and not self.high_volatility_mode:
            self.high_volatility_mode = True
            sessions, quality, _ = self.get_session_quality()
            session_text = ", ".join(sessions) if sessions else "No session"
            print(f"[{self.name}] HIGH VOLATILITY: {reason}")
            self._notify(
                f"HIGH VOLATILITY DETECTED!\n\nSession: {session_text}\nPairs: {reason}\n\n"
                f"Switching to STRICT mode:\nGOOD sessions - NO signals\nEXCELLENT - 5 conditions\n\n"
                f"Auto checks every {VOLATILITY_CHECK_MINS} mins"
            )
            self._notify_group(
                f"HIGH MARKET VOLATILITY!\n{reason}\n\nBot in STRICT MODE!\nOnly EXCELLENT session signals!"
            )
        elif not is_volatile and self.high_volatility_mode:
            self.high_volatility_mode = False
            print(f"[{self.name}] Volatility normalised")
            self._notify(
                "Volatility normalised!\n\nReturning to normal mode:\n"
                "EXCELLENT = 3 conditions\nGOOD = 3 conditions\nBoth sessions active again!"
            )
            self._notify_group("Volatility normalised! Both sessions active again.")
