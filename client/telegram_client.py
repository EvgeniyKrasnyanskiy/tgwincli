import asyncio
import logging

from telethon import TelegramClient, events
from telethon.tl.functions.updates import GetStateRequest

from client.handlers import EventHandlers
from config.settings import API_HASH, API_ID, PHONE


class TelegramClientManager:
    def __init__(self, gui):
        self.gui = gui
        self.client = None
        self.handlers = EventHandlers(gui)
        self.handlers_registered = False
        self.retry_delay_seconds = 5
        self.connection_monitor_task = None
        self.connection_check_interval = 10

    async def start(self):
        while not self.gui.is_closing:
            try:
                if self.client is None:
                    logging.info(f"Creating Telegram client with API_ID={API_ID}, PHONE={PHONE}")
                    self.client = TelegramClient("session_name", API_ID, API_HASH)
                    self.gui.client = self.client

                self.gui.set_status("\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a Telegram...", "connecting")
                logging.info("Connecting to Telegram...")
                await self.client.connect()
                logging.info("Connected successfully")

                if not await self.client.is_user_authorized():
                    self.gui.set_status("\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u043a\u043e\u0434\u0430 \u0432\u0445\u043e\u0434\u0430...", "connecting")
                    await self.authorize()
                else:
                    logging.info("User is already authorized")

                if not self.handlers_registered:
                    self.register_handlers()
                    self.handlers_registered = True

                await self.gui.load_dialogs()
                self.start_connection_monitor()
                self.gui.set_status("\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d", "online")
                await self.client.run_until_disconnected()
                await self.stop_connection_monitor()

                if self.gui.is_closing:
                    break

                logging.warning("Telegram client disconnected")
                self.gui.set_status(
                    f"\u0421\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u043e, \u043f\u043e\u0432\u0442\u043e\u0440 \u0447\u0435\u0440\u0435\u0437 {self.retry_delay_seconds} \u0441...",
                    "warning",
                )
            except Exception as e:
                if self.gui.is_closing:
                    break
                logging.exception("Error in client loop")
                self.gui.set_status(
                    f"\u041d\u0435\u0442 \u0441\u0435\u0442\u0438 / Telegram \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d, \u043f\u043e\u0432\u0442\u043e\u0440 \u0447\u0435\u0440\u0435\u0437 {self.retry_delay_seconds} \u0441...",
                    "error",
                )
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
                await asyncio.wait_for(self.client(GetStateRequest()), timeout=8)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.warning("Connection health check failed", exc_info=True)
                self.gui.set_status(
                    f"\u0421\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u043e, \u043f\u0435\u0440\u0435\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435...",
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
