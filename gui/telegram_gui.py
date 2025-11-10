import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import asyncio
import threading
import datetime
import platform
import os
import logging

from config.settings import API_ID, API_HASH, PHONE, TRUSTED_CONTACTS, WINDOW_WIDTH, WINDOW_HEIGHT
from client.telegram_client import TelegramClientManager
from utils.tray import create_tray_icon
from gui.widgets import create_chat_list, create_message_area, create_input_panel
from gui.popup import create_popup


class TelegramGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Client")

        # Центрируем окно
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width / 2) - (WINDOW_WIDTH / 2)
        y = (screen_height / 2) - (WINDOW_HEIGHT / 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{int(x)}+{int(y)}")
        self.root.withdraw()

        self.client = None
        self.current_chat = None
        self.loop = None
        self.dialogs = []
        self.tray_icon = None
        self.active_popups = []
        self.messages_dict = {}
        self.last_message_id = None
        self.blink_timers = {}  # Для хранения таймеров мигания

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.bind("<Unmap>", self.on_unmap)
        self.connect_to_telegram()

    def create_widgets(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.chat_listbox = create_chat_list(main_frame)
        self.chat_listbox.bind('<<ListboxSelect>>', self.on_chat_select)

        right_frame, self.messages_area = create_message_area(main_frame)

        callbacks = {
            'send': self.send_message,
            'attach': self.attach_file,
            'edit': self.edit_last_message
        }
        self.message_entry = create_input_panel(right_frame, callbacks)

        # Автофокус
        self.root.bind('<FocusIn>', lambda e: self.message_entry.focus_set())
        self.messages_area.bind('<Button-1>', lambda e: self.message_entry.focus_set())
        self.root.after(100, lambda: self.message_entry.focus_set())

    def connect_to_telegram(self):
        if not API_ID or not API_HASH or not PHONE:
            self.show_error("Создайте файл .env с параметрами:\n"
                            "API_ID=ваш_api_id\n"
                            "API_HASH=ваш_api_hash\n"
                            "PHONE=+ваш_номер\n"
                            "TRUSTED_CONTACTS=id1,id2")
            return

        if not TRUSTED_CONTACTS:
            self.show_warning("Список TRUSTED_CONTACTS пуст!\n"
                              "Добавьте ID контактов в .env")

        thread = threading.Thread(target=self.run_telegram_client, daemon=True)
        thread.start()

        tray_thread = threading.Thread(target=self.setup_tray, daemon=True)
        tray_thread.start()

    def run_telegram_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        client_manager = TelegramClientManager(self)
        self.loop.run_until_complete(client_manager.start())

    async def get_code_from_user(self):
        code_container = [None]

        def ask():
            code_container[0] = simpledialog.askstring(
                "Код подтверждения",
                f"Введите код на {PHONE}:",
                parent=self.root
            )

        self.root.after(0, ask)
        while code_container[0] is None:
            await asyncio.sleep(0.1)
        return code_container[0]

    async def get_password_from_user(self):
        password_container = [None]

        def ask():
            password_container[0] = simpledialog.askstring(
                "2FA",
                "Введите пароль:",
                parent=self.root,
                show='*'
            )

        self.root.after(0, ask)
        while password_container[0] is None:
            await asyncio.sleep(0.1)
        return password_container[0]

    async def load_dialogs(self):
        all_dialogs = await self.client.get_dialogs(limit=50)
        self.dialogs = [d for d in all_dialogs if getattr(d.entity, 'id', None) in TRUSTED_CONTACTS]
        self.root.after(0, lambda: self.chat_listbox.delete(0, tk.END))

        for dialog in self.dialogs:
            unread = getattr(dialog, 'unread_count', 0)
            name = getattr(dialog, 'name', None) or getattr(
                dialog.entity, 'title', str(getattr(dialog.entity, 'id', ''))
            )
            display_name = ("* " if unread > 0 else "") + name
            self.root.after(0, lambda n=display_name: self.chat_listbox.insert(tk.END, n))

    def update_unread_marks(self):
        self.chat_listbox.delete(0, tk.END)
        for dialog in self.dialogs:
            unread = getattr(dialog, 'unread_count', 0)
            name = getattr(dialog, 'name', None) or getattr(
                dialog.entity, 'title', str(getattr(dialog.entity, 'id', ''))
            )
            display_name = ("* " if unread > 0 else "") + name
            self.chat_listbox.insert(tk.END, display_name)

    def on_chat_select(self, event):
        selection = self.chat_listbox.curselection()
        if not selection:
            return

        self.current_chat = self.dialogs[selection[0]]

        if self.loop:
            asyncio.run_coroutine_threadsafe(self.load_messages(), self.loop)
            asyncio.run_coroutine_threadsafe(self.mark_as_read(), self.loop)

    async def load_messages(self):
        self.root.after(0, lambda: self.messages_area.config(state='normal'))
        self.root.after(0, lambda: self.messages_area.delete(1.0, tk.END))
        self.messages_dict.clear()

        msgs = await self.client.get_messages(self.current_chat, limit=50)
        for msg in reversed(msgs):
            if getattr(msg, 'message', None) or getattr(msg, 'media', None):
                msg_id = getattr(msg, 'id', None)
                if msg_id:
                    self.messages_dict[msg_id] = msg

                sender_name = "Я" if getattr(msg, 'out', False) else (
                    getattr(getattr(msg, 'sender', None), 'first_name', 'Unknown')
                    if getattr(msg, 'sender', None) else 'Unknown'
                )
                timestamp = msg.date.strftime("%Y-%m-%d %H:%M:%S") if getattr(msg, 'date', None) else ''
                message_text = getattr(msg, 'message', '')
                edited_mark = " (ред.)" if getattr(msg, 'edit_date', None) else ""

                media_info = ""
                if msg.media:
                    if msg.photo:
                        media_info = "[📷 Фото]"
                    elif msg.document:
                        media_info = "[📄 Файл]"
                    elif msg.video:
                        media_info = "[🎥 Видео]"
                    elif msg.voice:
                        media_info = "[🎤 Голосовое]"
                    elif msg.audio:
                        media_info = "[🎵 Аудио]"
                    else:
                        media_info = "[📎 Медиа]"

                text = f"[{timestamp}] {sender_name}: {message_text} {media_info}{edited_mark}".strip()
                self.root.after(0, lambda t=text: self.display_message(t))

        self.root.after(0, lambda: self.messages_area.config(state='disabled'))

    async def mark_as_read(self):
        """Отмечает все сообщения в текущем чате как прочитанные"""
        try:
            if self.current_chat:
                await self.client.send_read_acknowledge(self.current_chat)
                logging.info("Сообщения отмечены как прочитанные")
                await asyncio.sleep(0.5)
                await self.load_dialogs()
        except Exception as e:
            logging.error(f"Ошибка отметки: {e}")

    def display_message(self, message):
        self.messages_area.config(state='normal')
        self.messages_area.insert(tk.END, message + "\n")
        self.messages_area.see(tk.END)
        self.messages_area.config(state='disabled')

    def send_message(self):
        if not self.client or not self.current_chat:
            self.show_warning("Выберите чат!")
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        self.message_entry.delete(0, tk.END)

        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send_message_async(message), self.loop)

    async def send_message_async(self, message):
        try:
            sent_msg = await self.client.send_message(self.current_chat, message)
            self.last_message_id = getattr(sent_msg, 'id', None)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.display_message(f"[{timestamp}] Я: {message}"))
        except Exception as e:
            logging.exception("Ошибка отправки")
            self.root.after(0, lambda: self.show_error(f"Ошибка отправки: {e}"))

    def attach_file(self):
        if not self.client or not self.current_chat:
            self.show_warning("Выберите чат!")
            return

        filepath = filedialog.askopenfilename(
            title="Выберите файл для отправки",
            filetypes=[
                ("Все файлы", "*.*"),
                ("Изображения", "*.jpg *.jpeg *.png *.gif *.bmp"),
                ("Документы", "*.pdf *.doc *.docx *.txt"),
                ("Видео", "*.mp4 *.avi *.mkv"),
                ("Аудио", "*.mp3 *.wav *.ogg")
            ]
        )

        if filepath and self.loop:
            asyncio.run_coroutine_threadsafe(self.send_file_async(filepath), self.loop)

    async def send_file_async(self, filepath):
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)

            # Показываем начало отправки
            self.root.after(0, lambda: self.display_message(f"📤 Отправка: {filename} ({file_size // 1024} KB)"))

            # Прогресс-бар
            progress_text = f"⏳ Загрузка: 0%"
            self.root.after(0, lambda: self.display_message(progress_text))

            # Функция обратного вызова для прогресса
            def progress_callback(current, total):
                percent = int((current / total) * 100)
                bar_length = 20
                filled = int(bar_length * current / total)
                bar = '█' * filled + '░' * (bar_length - filled)
                progress_msg = f"⏳ {bar} {percent}%"

                # Обновляем последнюю строку
                self.root.after(0, lambda: self.update_last_message(progress_msg))

            # Отправка с прогрессом
            await self.client.send_file(
                self.current_chat,
                filepath,
                progress_callback=progress_callback
            )

            # Удаляем строку прогресса и показываем успех
            self.root.after(0, lambda: self.remove_last_message())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.display_message(f"[{timestamp}] Я: ✅ Отправлен файл: {filename}"))

        except Exception as e:
            logging.exception("Ошибка отправки файла")
            self.root.after(0, lambda: self.remove_last_message())
            self.root.after(0, lambda: self.display_message(f"❌ Ошибка отправки: {filename}"))
            self.root.after(0, lambda: self.show_error(f"Ошибка отправки файла: {e}"))

    def update_last_message(self, new_text):
        """Обновляет последнюю строку в области сообщений"""
        self.messages_area.config(state='normal')
        # Получаем содержимое
        content = self.messages_area.get(1.0, tk.END)
        lines = content.split('\n')

        # Удаляем последние 2 строки (последняя пустая + строка прогресса)
        if len(lines) >= 2:
            lines = lines[:-2]

        # Добавляем обновленный прогресс
        lines.append(new_text)

        # Обновляем содержимое
        self.messages_area.delete(1.0, tk.END)
        self.messages_area.insert(1.0, '\n'.join(lines) + '\n')
        self.messages_area.see(tk.END)
        self.messages_area.config(state='disabled')

    def remove_last_message(self):
        """Удаляет последнюю строку из области сообщений"""
        self.messages_area.config(state='normal')
        content = self.messages_area.get(1.0, tk.END)
        lines = content.split('\n')

        if len(lines) >= 2:
            lines = lines[:-2]  # Удаляем последнюю строку и пустую

        self.messages_area.delete(1.0, tk.END)
        self.messages_area.insert(1.0, '\n'.join(lines) + '\n')
        self.messages_area.config(state='disabled')

    def edit_last_message(self):
        if not self.client or not self.current_chat:
            self.show_warning("Выберите чат!")
            return

        if not self.last_message_id:
            self.show_warning("Нет сообщений для редактирования!")
            return

        new_text = simpledialog.askstring(
            "Редактировать сообщение",
            "Введите новый текст:",
            parent=self.root
        )

        if new_text and new_text.strip() and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.edit_message_async(self.last_message_id, new_text.strip()),
                self.loop
            )

    async def edit_message_async(self, message_id, new_text):
        try:
            await self.client.edit_message(self.current_chat, message_id, new_text)
            self.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                self.load_messages(), self.loop
            ))
            self.root.after(0, lambda: self.show_info("Сообщение отредактировано!"))
        except Exception as e:
            logging.exception("Ошибка редактирования")
            self.root.after(0, lambda: self.show_error(f"Ошибка редактирования: {e}"))

    def play_notification_sound(self):
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 500)
            except:
                pass

    def show_popup(self, sender_name, message, chat_id):
        self.close_all_popups()
        callbacks = {
            'on_reply': self.on_popup_reply,
            'on_close': self.on_popup_close
        }
        popup = create_popup(self.root, sender_name, message, chat_id, callbacks)
        self.active_popups.append(popup)

    def on_popup_reply(self, popup, chat_id):
        self.remove_popup(popup)
        self.toggle_window()
        for i, d in enumerate(self.dialogs):
            if getattr(d.entity, 'id', None) == chat_id:
                self.chat_listbox.select_set(i)
                self.on_chat_select(None)
                self.blink_chat_name(i)
                break

    def on_popup_close(self, popup, message, chat_id):
        self.remove_popup(popup)
        if self.loop:
            short_message = message[:50] + "..." if len(message) > 50 else message
            reply_text = f'Пользователь закрыл уведомление на сообщение: "{short_message}"'
            asyncio.run_coroutine_threadsafe(
                self.client.send_message(chat_id, reply_text),
                self.loop
            )

    def close_all_popups(self):
        for popup in self.active_popups[:]:
            try:
                popup.destroy()
            except:
                pass
        self.active_popups.clear()

    def remove_popup(self, popup):
        if popup in self.active_popups:
            self.active_popups.remove(popup)

    def blink_chat_name(self, index, duration=3000):
        """Мигание имени контакта зелёным цветом в течение заданного времени (в миллисекундах)"""
        # Отменяем предыдущее мигание для этого индекса
        if index in self.blink_timers:
            self.root.after_cancel(self.blink_timers[index])

        start_time = datetime.datetime.now()

        def blink():
            elapsed = (datetime.datetime.now() - start_time).total_seconds() * 1000

            if elapsed >= duration:
                # Возвращаем нормальный цвет
                self.chat_listbox.itemconfig(index, {'fg': 'black'})
                if index in self.blink_timers:
                    del self.blink_timers[index]
                return

            # Переключаем цвет
            current_color = self.chat_listbox.itemcget(index, 'fg')
            new_color = 'black' if current_color == 'green' else 'green'
            self.chat_listbox.itemconfig(index, {'fg': new_color})

            # Планируем следующее мигание
            timer = self.root.after(300, blink)
            self.blink_timers[index] = timer

        blink()

    def blink_chat_background(self):
        original_bg = self.messages_area.cget('bg')

        def blink(count=3, delay=300):
            if count == 0:
                self.messages_area.config(bg=original_bg)
                return
            color = '#90EE90' if count % 2 == 1 else original_bg
            self.messages_area.config(bg=color)
            self.root.after(delay, lambda: blink(count - 1, delay))

        blink()

    def setup_tray(self):
        def on_left_click(icon, item):
            self.root.after(0, self.toggle_window)

        def on_quit(icon, item):
            self.quit_app()

        self.tray_icon = create_tray_icon(on_left_click, on_quit)
        try:
            self.tray_icon.run()
        except Exception:
            logging.exception("Ошибка запуска трея")

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.message_entry.focus_set()

    def minimize_to_tray(self):
        self.root.withdraw()

    def on_unmap(self, event):
        if self.root.state() == 'iconic':
            self.root.withdraw()

    def quit_app(self):
        # Отменяем все таймеры мигания
        for timer in self.blink_timers.values():
            try:
                self.root.after_cancel(timer)
            except:
                pass
        self.blink_timers.clear()

        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except:
            pass
        if self.client and self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass
        self.root.destroy()

    def show_error(self, msg):
        messagebox.showerror("Ошибка", msg)

    def show_warning(self, msg):
        messagebox.showwarning("Предупреждение", msg)

    def show_info(self, msg):
        messagebox.showinfo("Информация", msg)