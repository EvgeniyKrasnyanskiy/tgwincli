import os
from dotenv import load_dotenv

load_dotenv()

# API настройки
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

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
