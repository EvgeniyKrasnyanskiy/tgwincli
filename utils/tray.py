import pystray

from utils.app_icon import get_tray_icon_image


def create_tray_icon(on_left_click, on_quit, on_settings=None):
    """Создаёт иконку в трее"""
    image = get_tray_icon_image(size=64)

    menu_items = [
        pystray.MenuItem('Открыть/Свернуть', on_left_click, default=True),
    ]
    if on_settings:
        menu_items.append(pystray.MenuItem('Настройки прокси...', on_settings))
    menu_items.append(pystray.MenuItem('Выход', on_quit))

    menu = pystray.Menu(*menu_items)

    return pystray.Icon('telegram_client', image, 'Telegram Client', menu)
