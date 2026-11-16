import os
from dotenv import load_dotenv

load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Admin login
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

DATABASE_URL = "sqlite:///./data/bot.db"
