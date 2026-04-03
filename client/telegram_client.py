import asyncio
import logging
from telethon import TelegramClient, events
from config.settings import API_ID, API_HASH, PHONE
from client.handlers import EventHandlers

# Пауза между попытками, если сеть/прокси недоступны (секунды)
RECONNECT_DELAY_INITIAL = 5
RECONNECT_DELAY_MAX = 90


class TelegramClientManager:
    def __init__(self, gui):
        self.gui = gui
        self.client = None
        self.handlers = EventHandlers(gui)
        self._session_alive = False
        self._reconnect_delay = RECONNECT_DELAY_INITIAL

    async def start(self):
        """Бесконечный цикл: подключение, работа, при обрыве — ожидание и снова подключение."""
        while True:
            try:
                await self._run_client_session()
            except Exception:
                logging.exception("Сессия Telegram завершилась с ошибкой")
            logging.info(
                "Повтор подключения к Telegram через %s с (прокси или сеть могут быть недоступны)",
                self._reconnect_delay,
            )
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(
                int(self._reconnect_delay * 1.5) + 1,
                RECONNECT_DELAY_MAX,
            )

    async def _run_client_session(self):
        logging.info("Создание клиента с API_ID=%s, PHONE=%s", API_ID, PHONE)
        self.client = TelegramClient("session_name", API_ID, API_HASH)
        self.gui.client = self.client

        logging.info("Подключение к Telegram...")
        await self.client.connect()
        self._reconnect_delay = RECONNECT_DELAY_INITIAL
        logging.info("Подключение успешно!")

        try:
            if not await self.client.is_user_authorized():
                await self.authorize()
            else:
                logging.info("Пользователь уже авторизован!")

            await self.gui.load_dialogs()
            self._session_alive = True
            self.schedule_updates()
            self.register_handlers()

            await self.client.run_until_disconnected()
        finally:
            self._session_alive = False
            await self._disconnect_client()

    async def _disconnect_client(self):
        if not self.client:
            self.gui.client = None
            return
        try:
            if self.client.is_connected():
                await self.client.disconnect()
        except Exception:
            logging.exception("Ошибка при отключении клиента")
        self.client = None
        self.gui.client = None

    async def _safe_load_dialogs(self):
        if not self._session_alive or not self.client:
            return
        try:
            await self.gui.load_dialogs()
        except Exception as e:
            logging.warning("Не удалось обновить список диалогов (сеть?): %s", e)

    async def authorize(self):
        """Авторизация пользователя"""
        try:
            logging.info("Отправка запроса кода на %s", PHONE)
            await self.client.send_code_request(PHONE, force_sms=True)
            logging.info("Код отправлен!")
            self.gui.root.after(
                0,
                lambda: self.gui.show_info("Код отправлен! Проверьте Telegram."),
            )
        except Exception as e:
            logging.error("Ошибка запроса кода: %s", e)
            self.gui.root.after(
                0,
                lambda: self.gui.show_error(f"Не удалось отправить код: {e}"),
            )
            raise

        self.gui.root.after(0, self.gui.root.deiconify)
        code = await self.gui.get_code_from_user()
        self.gui.root.after(0, self.gui.root.withdraw)

        if not code:
            raise RuntimeError("Код не введен")

        try:
            await self.client.sign_in(PHONE, code)
            logging.info("Авторизация успешна!")
        except Exception as e:
            if "password" in str(e).lower():
                self.gui.root.after(0, self.gui.root.deiconify)
                password = await self.gui.get_password_from_user()
                self.gui.root.after(0, self.gui.root.withdraw)
                if password:
                    await self.client.sign_in(password=password)
                    logging.info("Вход с паролем успешен!")
            else:
                raise

    def schedule_updates(self):
        """Планирование обновлений"""

        def tick():
            if not self._session_alive:
                return
            asyncio.run_coroutine_threadsafe(
                self._safe_load_dialogs(), self.gui.loop
            )
            if self._session_alive:
                self.gui.loop.call_later(5, tick)

        self.gui.loop.call_later(5, tick)

    def register_handlers(self):
        """Регистрация обработчиков событий"""
        self.client.add_event_handler(
            self.handlers.handle_new_message,
            events.NewMessage(incoming=True),
        )
        self.client.add_event_handler(
            self.handlers.handle_message_edited,
            events.MessageEdited,
        )
        self.client.add_event_handler(
            self.handlers.handle_message_deleted,
            events.MessageDeleted,
        )
