import os
from dotenv import load_dotenv

load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MY_PERSONAL_CHAT_ID = os.getenv("MY_PERSONAL_CHAT_ID", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

DATABASE_URL = "sqlite:///./data/bot.db"
