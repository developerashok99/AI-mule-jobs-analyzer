import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
NOTES_REPO = os.environ.get("NOTES_REPO", "Ashokkumarkarri/Notes")
NOTES_PATH = os.environ.get("NOTES_PATH", "Mulesoft/Study Notes")

TARGET_EXPERIENCE_MIN = int(os.environ.get("TARGET_EXPERIENCE_MIN", 3))
TARGET_EXPERIENCE_MAX = int(os.environ.get("TARGET_EXPERIENCE_MAX", 5))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "jobs.db")
