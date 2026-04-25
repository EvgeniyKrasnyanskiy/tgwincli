import logging
import asyncio
from config.settings import TRUSTED_CONTACTS
from utils.media import download_media


class EventHandlers:
    def __init__(self, gui):
        self.gui = gui

    def _current_chat_id(self):
        current_chat = self.gui.current_chat
        if not current_chat:
            return None
        return getattr(getattr(current_chat, "entity", current_chat), "id", None)

    def _is_current_chat(self, chat_id):
        return self._current_chat_id() == chat_id

    async def handle_new_message(self, event):
        """Обработка нового сообщения."""
        chat_id = getattr(event.chat_id, '__int__', lambda: event.chat_id)()
        if chat_id is None and event.message:
            chat_id = getattr(event.message, 'peer_id', None)
        if chat_id not in TRUSTED_CONTACTS:
            return

        message = getattr(event.message, 'message', '')
        sender = await event.get_sender()
        sender_name = getattr(sender, 'first_name', 'Unknown')
        timestamp = event.date.strftime("%Y-%m-%d %H:%M:%S") if event.date else ''

        media_info = ""
        media_path = None
        if event.message.media:
            try:
                media_result = await download_media(self.gui.client, event.message, sender_name, timestamp)
                media_info = media_result.get("text", "")
                media_path = media_result.get("path")
            except Exception as e:
                logging.error(f"Ошибка скачивания медиа: {e}")
                media_info = "[Ошибка загрузки медиа]"

        await self.gui.load_dialogs()

        chat_index = None
        for i, dialog in enumerate(self.gui.dialogs):
            if getattr(dialog.entity, 'id', None) == chat_id:
                chat_index = i
                break

        is_current_chat = self._is_current_chat(chat_id)
        window_is_visible = self.gui.root.winfo_viewable()

        if window_is_visible and chat_index is not None and not is_current_chat:
            self.gui.root.after(0, lambda idx=chat_index: self.gui.blink_chat_name(idx, duration=3000))

        if not window_is_visible or not is_current_chat:
            display_msg = f"{message} {media_info}".strip()
            self.gui.root.after(
                0,
                lambda sn=sender_name, dm=display_msg, ci=chat_id: self.gui.show_popup(sn, dm, ci),
            )
        else:
            self.gui.root.after(0, lambda: self.gui.blink_chat_background())

        if is_current_chat:
            body_text = f"{message} {media_info}".strip()
            self.gui.root.after(
                0,
                lambda sn=sender_name, ts=timestamp, bt=body_text, mp=media_path, mid=getattr(event.message, "id", None):
                self.gui.display_chat_message(sn, ts, bt, outgoing=False, message_id=mid, media_path=mp),
            )
            if window_is_visible:
                asyncio.run_coroutine_threadsafe(self.gui.mark_as_read(), self.gui.loop)

    async def handle_message_edited(self, event):
        """Обработка отредактированного сообщения."""
        chat_id = getattr(event.chat_id, '__int__', lambda: event.chat_id)()
        if chat_id is None and event.message:
            chat_id = getattr(event.message, 'peer_id', None)
        if chat_id not in TRUSTED_CONTACTS:
            return

        if self._is_current_chat(chat_id):
            self.gui.root.after(
                0,
                lambda: asyncio.run_coroutine_threadsafe(self.gui.load_messages(), self.gui.loop),
            )

    async def handle_message_deleted(self, event):
        """Обработка удаления сообщения."""
        if self.gui.current_chat:
            chat_id = self._current_chat_id()
            if chat_id in TRUSTED_CONTACTS:
                self.gui.root.after(
                    0,
                    lambda: asyncio.run_coroutine_threadsafe(self.gui.load_messages(), self.gui.loop),
                )
