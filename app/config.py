import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Для локального запуска без Telegram
TELEGRAM_BOT_TOKEN = "8579039126:AAFduTOX1YZKw0Y41T-rCWEuygLC_cVdSMw"
AUTHOR_USERNAME = "author_example"
BOT_NAME = "Каталог фигурок"
WEBAPP_URL = "https://authorless-theo-apogeotropic.ngrok-free.dev"

# Настройки для локальной разработки
DEBUG = True
HOST = "0.0.0.0"
PORT = 8000