import pystray
from PIL import Image, ImageDraw

def create_tray_icon(on_left_click, on_quit):
    """Создаёт иконку в трее"""
    size = 64
    image = Image.new('RGB', (size, size), color=(0, 136, 204))
    draw = ImageDraw.Draw(image)

    # Рисуем самолётик Telegram
    plane = [
        (size * 0.25, size * 0.75),
        (size * 0.80, size * 0.55),
        (size * 0.35, size * 0.25)
    ]
    rotated = [(size - x, size - y) for (x, y) in plane]
    draw.polygon(rotated, fill="white")

    tail_start = (size * 0.25, size * 0.75)
    tail_end = (size * 0.575, size * 0.450)
    draw.line([tail_start, tail_end], fill=(0, 136, 204), width=int(size * 0.08))

    menu = pystray.Menu(
        pystray.MenuItem('Открыть/Свернуть', on_left_click, default=True),
        pystray.MenuItem('Выход', on_quit)
    )

    return pystray.Icon('telegram_client', image, 'Telegram Client', menu)