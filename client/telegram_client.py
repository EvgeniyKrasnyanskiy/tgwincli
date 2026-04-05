import logging

from telethon import TelegramClient, events

from client.handlers import EventHandlers
from config.settings import API_HASH, API_ID, PHONE


class TelegramClientManager:
    def __init__(self, gui):
        self.gui = gui
        self.client = None
        self.handlers = EventHandlers(gui)

    async def start(self):
        try:
            logging.info(f"Creating Telegram client with API_ID={API_ID}, PHONE={PHONE}")
            self.client = TelegramClient("session_name", API_ID, API_HASH)
            self.gui.client = self.client

            logging.info("Connecting to Telegram...")
            await self.client.connect()
            logging.info("Connected successfully")

            if not await self.client.is_user_authorized():
                await self.authorize()
            else:
                logging.info("User is already authorized")

            await self.gui.load_dialogs()
            self.register_handlers()

            await self.client.run_until_disconnected()

        except Exception as e:
            logging.exception("Error in client start")
            self.gui.root.after(
                0,
                lambda: self.gui.show_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f:\n{str(e)}"),
            )

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
            return

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
