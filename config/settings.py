import os
from dotenv import load_dotenv

load_dotenv()

# API настройки
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

# Proxy settings
PROXY_MODE = os.getenv("PROXY_MODE", "auto").strip().lower()
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1").strip()
PROXY_PORT = int(os.getenv("PROXY_PORT", "10808"))
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "").strip()
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "").strip()
PROXY_SECRET = os.getenv("PROXY_SECRET", "").strip()
PROXY_CONNECT_TIMEOUT = int(os.getenv("PROXY_CONNECT_TIMEOUT", "12"))

# Контакты
TRUSTED_CONTACTS = os.getenv("TRUSTED_CONTACTS", "")
TRUSTED_CONTACTS = [int(x.strip()) for x in TRUSTED_CONTACTS.split(",") if x.strip().isdigit()]

# Папка для медиа
MEDIA_DIR = "media"
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# UI настройки
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
POPUP_BASE_WIDTH = 400
POPUP_BASE_HEIGHT = 200
