import pystray

from utils.app_icon import get_tray_icon_image


def create_tray_icon(on_left_click, on_quit):
    """Создаёт иконку в трее"""
    image = get_tray_icon_image(size=64)

    menu = pystray.Menu(
        pystray.MenuItem('Открыть/Свернуть', on_left_click, default=True),
        pystray.MenuItem('Выход', on_quit)
    )

    return pystray.Icon('telegram_client', image, 'Telegram Client', menu)
