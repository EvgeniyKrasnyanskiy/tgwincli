import logging
from utils.media import download_media
from config.settings import TRUSTED_CONTACTS


class EventHandlers:
    def __init__(self, gui):
        self.gui = gui

    async def handle_new_message(self, event):
        """Обработка новых сообщений"""
        chat_id = getattr(event.chat_id, '__int__', lambda: event.chat_id)()
        if chat_id is None and event.message:
            chat_id = getattr(event.message, 'peer_id', None)
        if chat_id not in TRUSTED_CONTACTS:
            return

        message = getattr(event.message, 'message', '')
        sender = await event.get_sender()
        sender_name = getattr(sender, 'first_name', 'Unknown')
        timestamp = event.date.strftime("%Y-%m-%d %H:%M:%S") if event.date else ''

        # Обработка медиа
        media_info = ""
        if event.message.media:
            try:
                media_info = await download_media(self.gui.client, event.message, sender_name, timestamp)
            except Exception as e:
                logging.error(f"Ошибка скачивания медиа: {e}")
                media_info = "[Ошибка загрузки файла]"

        if not any(getattr(d.entity, 'id', None) == chat_id for d in self.gui.dialogs):
            await self.gui.load_dialogs()

        # Находим индекс чата для мигания
        chat_index = None
        for i, d in enumerate(self.gui.dialogs):
            if getattr(d.entity, 'id', None) == chat_id:
                chat_index = i
                break

        if not self.gui.root.winfo_viewable():
            display_msg = f"{message} {media_info}".strip()
            self.gui.root.after(0, lambda sn=sender_name, dm=display_msg, ci=chat_id:
            self.gui.show_popup(sn, dm, ci))
            self.gui.play_notification_sound()
        else:
            # Мигаем именем контакта даже если открыт другой чат
            if chat_index is not None:
                self.gui.root.after(0, lambda idx=chat_index: self.gui.blink_chat_name(idx, duration=3000))

            if self.gui.current_chat and getattr(self.gui.current_chat, 'id', None) == chat_id:
                self.gui.root.after(0, lambda: self.gui.blink_chat_background())

        if self.gui.current_chat and getattr(self.gui.current_chat, 'id', None) == chat_id:
            display_text = f"[{timestamp}] {sender_name}: {message} {media_info}".strip()
            self.gui.root.after(0, lambda dt=display_text: self.gui.display_message(dt))
            if self.gui.root.winfo_viewable():
                import asyncio
                asyncio.run_coroutine_threadsafe(self.gui.mark_as_read(), self.gui.loop)

        self.gui.root.after(0, lambda: self.gui.update_unread_marks())

    async def handle_message_edited(self, event):
        """Обработка редактирования сообщений"""
        chat_id = getattr(event.chat_id, '__int__', lambda: event.chat_id)()
        if chat_id is None and event.message:
            chat_id = getattr(event.message, 'peer_id', None)
        if chat_id not in TRUSTED_CONTACTS:
            return

        if self.gui.current_chat and getattr(self.gui.current_chat, 'id', None) == chat_id:
            import asyncio
            self.gui.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                self.gui.load_messages(), self.gui.loop
            ))

    async def handle_message_deleted(self, event):
        """Обработка удаления сообщений"""
        if self.gui.current_chat:
            chat_id = getattr(self.gui.current_chat, 'id', None)
            if chat_id in TRUSTED_CONTACTS:
                import asyncio
                self.gui.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                    self.gui.load_messages(), self.gui.loop
                ))