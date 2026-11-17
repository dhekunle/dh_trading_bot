import os
from dotenv import load_dotenv

load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")  # optional now
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")          # Patience Bot group
TELEGRAM_CHAT_ID_3MIN = os.getenv("TELEGRAM_CHAT_ID_3MIN", "") # 3 min Bot group
MY_PERSONAL_CHAT_ID = os.getenv("MY_PERSONAL_CHAT_ID", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Admin login
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

DATABASE_URL = "sqlite:///./data/bot.db"
