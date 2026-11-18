import os
from dotenv import load_dotenv

load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")  # optional now
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")                 # Patience Bot Groq key
GROQ_API_KEY_3MIN = os.getenv("GROQ_API_KEY_3MIN", "")       # 3 min Bot Groq key
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")                 # Patience Bot token
TELEGRAM_BOT_TOKEN_3MIN = os.getenv("TELEGRAM_BOT_TOKEN_3MIN", "")       # 3 min Bot token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")                     # Patience Bot group
TELEGRAM_CHAT_ID_3MIN = os.getenv("TELEGRAM_CHAT_ID_3MIN", "")           # 3 min Bot group
MY_PERSONAL_CHAT_ID = os.getenv("MY_PERSONAL_CHAT_ID", "")               # Personal for Patience
MY_PERSONAL_CHAT_ID_3MIN = os.getenv("MY_PERSONAL_CHAT_ID_3MIN", "")     # Personal for 3 min
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Admin login
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Use a hosted Postgres database (set DATABASE_URL) so accounts survive redeploys.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/bot.db")
# Accept any Postgres style prefix (Supabase shows several) and always use the psycopg 3 driver
for _prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
    if DATABASE_URL.startswith(_prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(_prefix):]
        break

# When on, new accounts must be enabled by the admin before they can see signals
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "0").strip().lower() in ("1", "true", "yes")
