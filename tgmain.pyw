import ctypes
import os

try:
    APP_USER_MODEL_ID = "Parsers.TgClient.TelegramClient.1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
except Exception as e:
    print(f"Error setting AppID: {e}")

import tkinter as tk
import logging
from utils.app_icon import ensure_icon_files, set_window_icon
from gui.telegram_gui import TelegramGUI

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    ensure_icon_files()
    root = tk.Tk()
    set_window_icon(root)
    app = TelegramGUI(root)
    root.mainloop()
