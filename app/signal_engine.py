"""
Patience Bot engine (the original Normal Signal Bot logic).
All the shared logic lives in engine_core.py.
"""
from .config import GROQ_API_KEY
from .engine_core import BaseEngine, PAIRS, WAT  # noqa: F401  (re-exported)


class SignalEngine(BaseEngine):
    name = "Patience Bot"

    def __init__(self):
        super().__init__(GROQ_API_KEY)
