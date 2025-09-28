import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

API_ID = int(os.getenv('API_ID', '20288994'))
API_HASH = os.getenv('API_HASH', 'd702614912f1ad370a0d18786002adbf')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8314502536:AAFLGwBTzCXPxvBPC5oMIiSKVyDaY5sm5mY')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1002995694885'))  # -100xxxxx for private channels
BASE_URL = os.getenv('BASE_URL', 'https://your-domain.example')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 4 * 1024 * 1024 * 1024))  # default 4GB

# SQLite DB file
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'filmzi.db'))

# Optional: debug
DEBUG = os.getenv('DEBUG', '0') in ('1', 'true', 'True')
