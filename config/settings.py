import os
from dotenv import load_dotenv

load_dotenv()

# API настройки
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Proxy settings
PROXY_MODE = os.getenv("PROXY_MODE", "auto").strip().lower()
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1").strip()
PROXY_PORT = int(os.getenv("PROXY_PORT", "1443"))
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "").strip()
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "").strip()
PROXY_SECRET = os.getenv("PROXY_SECRET", "").strip()
PROXY_CONNECT_TIMEOUT = int(os.getenv("PROXY_CONNECT_TIMEOUT", "12"))


def get_proxy_settings():
    return {
        "mode": PROXY_MODE,
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "username": PROXY_USERNAME,
        "password": PROXY_PASSWORD,
        "secret": PROXY_SECRET,
        "timeout": PROXY_CONNECT_TIMEOUT,
    }


def save_proxy_settings(new_settings):
    global PROXY_MODE, PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD, PROXY_SECRET, PROXY_CONNECT_TIMEOUT

    from dotenv import set_key

    if "mode" in new_settings:
        PROXY_MODE = str(new_settings["mode"]).strip().lower()
        os.environ["PROXY_MODE"] = PROXY_MODE
        set_key(ENV_FILE_PATH, "PROXY_MODE", PROXY_MODE)

    if "host" in new_settings:
        PROXY_HOST = str(new_settings["host"]).strip()
        os.environ["PROXY_HOST"] = PROXY_HOST
        set_key(ENV_FILE_PATH, "PROXY_HOST", PROXY_HOST)

    if "port" in new_settings:
        PROXY_PORT = int(new_settings["port"])
        os.environ["PROXY_PORT"] = str(PROXY_PORT)
        set_key(ENV_FILE_PATH, "PROXY_PORT", str(PROXY_PORT))

    if "username" in new_settings:
        PROXY_USERNAME = str(new_settings["username"]).strip()
        os.environ["PROXY_USERNAME"] = PROXY_USERNAME
        set_key(ENV_FILE_PATH, "PROXY_USERNAME", PROXY_USERNAME)

    if "password" in new_settings:
        PROXY_PASSWORD = str(new_settings["password"]).strip()
        os.environ["PROXY_PASSWORD"] = PROXY_PASSWORD
        set_key(ENV_FILE_PATH, "PROXY_PASSWORD", PROXY_PASSWORD)

    if "secret" in new_settings:
        PROXY_SECRET = str(new_settings["secret"]).strip()
        os.environ["PROXY_SECRET"] = PROXY_SECRET
        set_key(ENV_FILE_PATH, "PROXY_SECRET", PROXY_SECRET)

    if "timeout" in new_settings:
        PROXY_CONNECT_TIMEOUT = int(new_settings["timeout"])
        os.environ["PROXY_CONNECT_TIMEOUT"] = str(PROXY_CONNECT_TIMEOUT)
        set_key(ENV_FILE_PATH, "PROXY_CONNECT_TIMEOUT", str(PROXY_CONNECT_TIMEOUT))


def detect_tgws_proxy():
    import json
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    tgws_config = os.path.join(appdata, "TgWsProxy", "config.json")
    if not os.path.isfile(tgws_config):
        return None
    try:
        with open(tgws_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "mode": "mtproto",
            "host": data.get("host", "127.0.0.1"),
            "port": int(data.get("port", 1443)),
            "secret": data.get("secret", "").strip(),
        }
    except Exception:
        return None


def test_proxy_connection(host, port, timeout=5):
    import socket
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, "Соединение успешно установлено"
    except Exception as e:
        return False, str(e)


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
