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


# ---------------------------------------------------------------- profile + chat
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
RESERVED_USERNAMES = {"admin", "administrator", "support", "moderator", "mod", "staff", "owner",
                      "root", "system", "official", "help", "dh", "dhbinarytrader", "dhbinary"}
LINK_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/|wa\.me/|\b[a-z0-9\-]+\.(com|net|org|io|me|co|ly|app|xyz|info)\b)", re.I)


def clean_name(name: str) -> str:
    return " ".join((name or "").split())


def name_problem(name: str):
    if len(name) < 2 or len(name) > 60:
        return "Please enter your full name (2 to 60 characters)."
    letters = sum(1 for ch in name if ch.isalpha())
    if letters < 2 or not all(ch.isalpha() or ch in " .'-" for ch in name):
        return "Your name can only contain letters, spaces, dots, hyphens and apostrophes."
    return None


def clean_username(username: str) -> str:
    return (username or "").strip().lower().lstrip("@")


def username_problem(username: str):
    if not USERNAME_RE.match(username):
        return "Username must be 3 to 20 characters: letters, numbers and underscores only."
    if username in RESERVED_USERNAMES or username.startswith("admin"):
        return "That username is reserved. Please choose another."
    return None


def clean_chat_text(text: str) -> str:
    """Single line, no control characters, trimmed."""
    text = "".join(ch if ch.isprintable() else " " for ch in (text or ""))
    return " ".join(text.split())


def has_link(text: str) -> bool:
    return bool(LINK_RE.search(text or ""))
