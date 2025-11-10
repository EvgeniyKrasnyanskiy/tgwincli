import asyncio
import logging
from telethon import TelegramClient, events
from config.settings import API_ID, API_HASH, PHONE
from client.handlers import EventHandlers


class TelegramClientManager:
    def __init__(self, gui):
        self.gui = gui
        self.client = None
        self.handlers = EventHandlers(gui)

    async def start(self):
        """Запуск клиента"""
        try:
            logging.info(f"Создание клиента с API_ID={API_ID}, PHONE={PHONE}")
            self.client = TelegramClient('session_name', API_ID, API_HASH)
            self.gui.client = self.client

            logging.info("Подключение к Telegram...")
            await self.client.connect()
            logging.info("Подключение успешно!")

            if not await self.client.is_user_authorized():
                await self.authorize()
            else:
                logging.info("Пользователь уже авторизован!")

            await self.gui.load_dialogs()
            self.schedule_updates()
            self.register_handlers()

            await self.client.run_until_disconnected()

        except Exception as e:
            logging.exception("Ошибка в start_client")
            self.gui.root.after(0, lambda: self.gui.show_error(f"Ошибка подключения:\n{str(e)}"))

    async def authorize(self):
        """Авторизация пользователя"""
        try:
            logging.info(f"Отправка запроса кода на {PHONE}")
            result = await self.client.send_code_request(PHONE, force_sms=True)
            logging.info(f"Код отправлен!")
            self.gui.root.after(0, lambda: self.gui.show_info("Код отправлен! Проверьте Telegram."))
        except Exception as e:
            logging.error(f"Ошибка запроса кода: {e}")
            self.gui.root.after(0, lambda: self.gui.show_error(f"Не удалось отправить код: {e}"))
            return

        self.gui.root.after(0, self.gui.root.deiconify)
        code = await self.gui.get_code_from_user()
        self.gui.root.after(0, self.gui.root.withdraw)

        if not code:
            raise Exception("Код не введен")

        try:
            await self.client.sign_in(PHONE, code)
            logging.info("Авторизация успешна!")
        except Exception as e:
            if 'password' in str(e).lower():
                self.gui.root.after(0, self.gui.root.deiconify)
                password = await self.gui.get_password_from_user()
                self.gui.root.after(0, self.gui.root.withdraw)
                if password:
                    await self.client.sign_in(password=password)
                    logging.info("Вход с паролем успешен!")
            else:
                raise e

    def schedule_updates(self):
        """Планирование обновлений"""

        def update():
            asyncio.run_coroutine_threadsafe(self.gui.load_dialogs(), self.gui.loop)
            self.gui.loop.call_later(5, update)

        self.gui.loop.call_later(5, update)

    def register_handlers(self):
        """Регистрация обработчиков событий"""
        self.client.add_event_handler(
            self.handlers.handle_new_message,
            events.NewMessage(incoming=True)
        )
        self.client.add_event_handler(
            self.handlers.handle_message_edited,
            events.MessageEdited
        )
        self.client.add_event_handler(
            self.handlers.handle_message_deleted,
            events.MessageDeleted
        )