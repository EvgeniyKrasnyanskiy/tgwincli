import os
import tempfile
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw


ICON_DIR = Path(tempfile.gettempdir()) / "tgclient"
ICON_PNG_PATH = ICON_DIR / "app_icon.png"
ICON_ICO_PATH = ICON_DIR / "app_icon.ico"


def create_messenger_icon(size=256):
    """Build a small messenger-like icon for the app window and tray."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    padding = int(size * 0.08)
    bubble_box = (padding, padding, size - padding, size - padding)
    bubble_color = (34, 139, 230, 255)
    draw.ellipse(bubble_box, fill=bubble_color)

    tail = [
        (int(size * 0.38), int(size * 0.84)),
        (int(size * 0.52), int(size * 0.72)),
        (int(size * 0.58), int(size * 0.90)),
    ]
    draw.polygon(tail, fill=bubble_color)

    plane = [
        (int(size * 0.28), int(size * 0.50)),
        (int(size * 0.73), int(size * 0.33)),
        (int(size * 0.47), int(size * 0.70)),
    ]
    draw.polygon(plane, fill="white")
    draw.line(
        [
            (int(size * 0.33), int(size * 0.53)),
            (int(size * 0.47), int(size * 0.70)),
            (int(size * 0.54), int(size * 0.49)),
        ],
        fill=bubble_color,
        width=max(4, size // 24),
    )

    return image


def ensure_icon_files():
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon = create_messenger_icon()
    icon.save(ICON_PNG_PATH, format="PNG")
    icon.save(
        ICON_ICO_PATH,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    return str(ICON_PNG_PATH), str(ICON_ICO_PATH)


def set_window_icon(root):
    png_path, ico_path = ensure_icon_files()

    try:
        root.iconbitmap(default=ico_path)
    except tk.TclError:
        pass

    try:
        root._app_icon_image = tk.PhotoImage(file=png_path)
        root.iconphoto(True, root._app_icon_image)
    except tk.TclError:
        pass

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tgclient.messenger")
        except Exception:
            pass


def get_tray_icon_image(size=64):
    return create_messenger_icon(size=size)
