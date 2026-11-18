"""
Accounts and sessions: password hashing, email checks and login throttling.
Only the Python standard library is used here.
"""
import hashlib
import hmac
import re
import secrets
import time

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
ITERATIONS = 200_000
UNSET_ADMIN_PASSWORDS = {"", "admin123", "your_secure_password", "change_me"}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = (stored or "").split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def clean_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_RE.match(email))


def password_problem(password: str):
    """Returns a message if the password is not acceptable, otherwise None."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password is too long."
    return None


def admin_configured(admin_password: str) -> bool:
    return (admin_password or "") not in UNSET_ADMIN_PASSWORDS


def admin_credentials_ok(username, password, expected_user, expected_password) -> bool:
    if not admin_configured(expected_password):
        return False
    user_ok = hmac.compare_digest((username or "").encode("utf-8"), (expected_user or "").encode("utf-8"))
    pass_ok = hmac.compare_digest((password or "").encode("utf-8"), (expected_password or "").encode("utf-8"))
    return user_ok and pass_ok


class Throttle:
    """Allows a limited number of failed attempts per key in a time window."""

    def __init__(self, limit: int = 8, window: int = 900):
        self.limit, self.window, self.hits = limit, window, {}

    def _recent(self, key):
        cutoff = time.time() - self.window
        self.hits[key] = [t for t in self.hits.get(key, []) if t > cutoff]
        return self.hits[key]

    def blocked(self, key) -> bool:
        return len(self._recent(key)) >= self.limit

    def fail(self, key):
        self._recent(key).append(time.time())

    def clear(self, key):
        self.hits.pop(key, None)
