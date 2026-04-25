import asyncio
import logging

from telethon import TelegramClient, events, connection
from telethon.tl.functions.updates import GetStateRequest

from client.handlers import EventHandlers
from config.settings import (
    API_HASH,
    API_ID,
    PHONE,
    PROXY_HOST,
    PROXY_MODE,
    PROXY_PASSWORD,
    PROXY_PORT,
    PROXY_SECRET,
    PROXY_USERNAME,
    PROXY_CONNECT_TIMEOUT,
)


class TelegramClientManager:
    def __init__(self, gui):
        self.gui = gui
        self.client = None
        self.handlers = EventHandlers(gui)
        self.handlers_registered = False
        self.retry_delay_seconds = 5
        self.connection_monitor_task = None
        self.connection_check_interval = 15
        self.connection_check_timeout = 12
        self.connection_failures = 0
        self.max_connection_failures = 3

    def _build_client_args(self, mode):
        if mode in ("", "none", "off", "direct", "auto"):
            logging.info("Proxy disabled, using direct Telegram connection.")
            return {}

        if mode in ("socks", "socks5"):
            import socks

            proxy = (socks.SOCKS5, PROXY_HOST, PROXY_PORT)
            if PROXY_USERNAME or PROXY_PASSWORD:
                proxy = (
                    socks.SOCKS5,
                    PROXY_HOST,
                    PROXY_PORT,
                    True,
                    PROXY_USERNAME,
                    PROXY_PASSWORD,
                )

            logging.info("Initializing through SOCKS5 proxy %s:%s...", PROXY_HOST, PROXY_PORT)
            return {"proxy": proxy}

        if mode in ("mtproto", "mtproxy"):
            if not PROXY_SECRET:
                raise ValueError("PROXY_SECRET is required for MTProto mode")

            logging.info("Initializing through MTProto proxy %s:%s...", PROXY_HOST, PROXY_PORT)
            return {
                "connection": connection.ConnectionTcpMTProxyRandomizedIntermediate,
                "proxy": (PROXY_HOST, PROXY_PORT, PROXY_SECRET),
            }

        raise ValueError(f"Unsupported PROXY_MODE: {PROXY_MODE}")

    def _create_client(self, mode):
        client_args = self._build_client_args(mode)
        client = TelegramClient(
            "client_session",
            API_ID,
            API_HASH,
            **client_args,
        )
        self.client = client
        self.gui.client = client
        self.handlers_registered = False
        return client

    async def _disconnect_current_client(self):
        if not self.client:
            return
        try:
            await self.client.disconnect()
        except Exception:
            logging.debug("Client disconnect failed", exc_info=True)
        finally:
            self.client = None
            self.gui.client = None
            self.handlers_registered = False

    async def _connect_startup_client(self):
        mode = (PROXY_MODE or "auto").strip().lower()
        timeout_seconds = max(1, PROXY_CONNECT_TIMEOUT)
        await self._disconnect_current_client()

        if mode == "auto":
            self._create_client("direct")
            self.gui.set_status("Подключение к Telegram напрямую...", "connecting")
            try:
                await asyncio.wait_for(self.client.connect(), timeout=timeout_seconds)
                logging.info("Connected to Telegram directly.")
                return
            except asyncio.TimeoutError:
                logging.warning("Direct Telegram connection timed out after %s seconds.", timeout_seconds)
                self.gui.set_status("Прямое подключение не отвечает, пробую MTProto proxy...", "warning")
            except Exception as e:
                logging.warning("Direct Telegram connection failed, trying MTProto proxy: %s", e)
                self.gui.set_status("Прямое подключение не удалось, пробую MTProto proxy...", "warning")

            await self._disconnect_current_client()

            if not PROXY_SECRET:
                raise ValueError("PROXY_SECRET is required for PROXY_MODE=auto MTProto fallback")

            self._create_client("mtproto")
            await asyncio.wait_for(self.client.connect(), timeout=timeout_seconds)
            logging.info("Connected to Telegram through MTProto proxy.")
            return

        self._create_client(mode)
        self.gui.set_status("Подключение к Telegram...", "connecting")
        await asyncio.wait_for(self.client.connect(), timeout=timeout_seconds)

    async def start(self):
        while not self.gui.is_closing:
            try:
                if self.client is None or not self.client.is_connected():
                    await self._connect_startup_client()

                logging.info("Successfully connected to Telegram")

                # Проверка авторизации
                if not await self.client.is_user_authorized():
                    self.gui.set_status("Ожидание кода входа...", "connecting")
                    await self.authorize()
                else:
                    logging.info("User is already authorized")

                # Регистрация обработчиков (событий)
                if not self.handlers_registered:
                    self.register_handlers()
                    self.handlers_registered = True

                # Загрузка интерфейса
                await self.gui.load_dialogs()
                self.connection_failures = 0
                self.start_connection_monitor()

                self.gui.set_status("Подключен", "online")

                # Важно: ждем, пока клиент работает
                await self.client.run_until_disconnected()

            except Exception:
                if self.gui.is_closing:
                    break
                logging.exception("Error in client loop")
                self.gui.set_status(
                    f"Ошибка сети: повтор через {self.retry_delay_seconds} сек...",
                    "error"
                )
                await self._disconnect_current_client()

            await self.stop_connection_monitor()
            await asyncio.sleep(self.retry_delay_seconds)

    def start_connection_monitor(self):
        if self.connection_monitor_task and not self.connection_monitor_task.done():
            return
        self.connection_monitor_task = asyncio.create_task(self.monitor_connection())

    async def stop_connection_monitor(self):
        if not self.connection_monitor_task:
            return
        self.connection_monitor_task.cancel()
        try:
            await self.connection_monitor_task
        except asyncio.CancelledError:
            pass
        self.connection_monitor_task = None

    async def monitor_connection(self):
        while not self.gui.is_closing:
            await asyncio.sleep(self.connection_check_interval)
            if self.gui.is_closing or not self.client:
                return
            if not self.client.is_connected():
                self.gui.set_status(
                    f"\u0421\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u043e, \u043f\u043e\u0432\u0442\u043e\u0440 \u0447\u0435\u0440\u0435\u0437 {self.retry_delay_seconds} \u0441...",
                    "warning",
                )
                return
            try:
                await asyncio.wait_for(
                    self.client(GetStateRequest()),
                    timeout=self.connection_check_timeout,
                )
                if self.connection_failures > 0:
                    self.gui.set_status("\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d", "online")
                self.connection_failures = 0
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                self.connection_failures += 1
                logging.warning(
                    "Connection health check timed out (%s/%s)",
                    self.connection_failures,
                    self.max_connection_failures,
                )
            except Exception as e:
                self.connection_failures += 1
                logging.warning(
                    "Connection health check failed (%s/%s): %s",
                    self.connection_failures,
                    self.max_connection_failures,
                    e,
                )

            if self.connection_failures < self.max_connection_failures:
                continue

            self.gui.set_status(
                "\u0421\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u043e, \u043f\u0435\u0440\u0435\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435...",
                "warning",
            )
            try:
                await self.client.disconnect()
            except Exception:
                logging.debug("Disconnect after failed health check also failed", exc_info=True)
            return

    async def authorize(self):
        try:
            logging.info(f"Requesting login code for {PHONE}")
            await self.client.send_code_request(PHONE, force_sms=True)
            logging.info("Login code sent")
            self.gui.root.after(
                0,
                lambda: self.gui.show_info("\u041a\u043e\u0434 \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d! \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 Telegram."),
            )
        except Exception as e:
            logging.error(f"Code request failed: {e}")
            self.gui.root.after(
                0,
                lambda: self.gui.show_error(f"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043a\u043e\u0434: {e}"),
            )
            raise

        self.gui.root.after(0, self.gui.root.deiconify)
        code = await self.gui.get_code_from_user()
        self.gui.root.after(0, self.gui.root.withdraw)

        if not code:
            raise Exception("\u041a\u043e\u0434 \u043d\u0435 \u0432\u0432\u0435\u0434\u0435\u043d")

        try:
            await self.client.sign_in(PHONE, code)
            logging.info("Authorization successful")
        except Exception as e:
            if "password" in str(e).lower():
                self.gui.root.after(0, self.gui.root.deiconify)
                password = await self.gui.get_password_from_user()
                self.gui.root.after(0, self.gui.root.withdraw)
                if password:
                    await self.client.sign_in(password=password)
                    logging.info("Authorization with 2FA successful")
            else:
                raise

    def register_handlers(self):
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
