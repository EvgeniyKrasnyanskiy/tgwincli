import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, filedialog
from telethon import TelegramClient, events
import asyncio
import threading
import logging
import datetime
import platform
import pystray
from PIL import Image, ImageDraw

from dotenv import load_dotenv
import os

# Включаем логирование для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Загружаем переменные окружения
load_dotenv()

# ============================================
# ВАЖНО: Создайте файл .env в корне проекта
# со следующими параметрами:
# API_ID=ваш_api_id
# API_HASH=ваш_api_hash
# PHONE=+ваш_номер_телефона
# TRUSTED_CONTACTS=94361431,123456789
# ============================================
API_ID = int(os.getenv("API_ID", 0))  # Преобразуем в int
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

# Список ID контактов для отображения (только эти чаты будут видны)
TRUSTED_CONTACTS = os.getenv("TRUSTED_CONTACTS", "")
TRUSTED_CONTACTS = [int(x.strip()) for x in TRUSTED_CONTACTS.split(",") if x.strip().isdigit()]

# Папка для сохранения медиа
MEDIA_DIR = "media"
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)


class TelegramGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Client")
        self.root.geometry("800x600")
        self.root.withdraw()  # Скрываем основное окно по умолчанию

        self.client = None
        self.current_chat = None
        self.loop = None
        self.dialogs = []
        self.tray_icon = None
        self.active_popups = []  # Список активных popup окон
        self.messages_dict = {}  # Словарь для хранения сообщений {message_id: message_object}
        self.last_message_id = None  # ID последнего отправленного сообщения

        self.create_widgets()

        # Переопределяем закрытие и минимизацию
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.bind("<Unmap>", self.on_unmap)

        # Запускаем подключение и tray в отдельных потоках
        self.connect_to_telegram()

    def create_widgets(self):
        # Основная область (минималистично)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Левая панель - список чатов (только из TRUSTED_CONTACTS)
        left_frame = tk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

        tk.Label(left_frame, text="Список контактов:", font=("Arial", 10, "bold")).pack()

        self.chat_listbox = tk.Listbox(left_frame, width=25)
        self.chat_listbox.pack(fill=tk.BOTH, expand=True)
        self.chat_listbox.bind('<<ListboxSelect>>', self.on_chat_select)

        # Правая панель - сообщения
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right_frame, text="История сообщений:", font=("Arial", 10, "bold")).pack()

        self.messages_area = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD,
                                                       state='disabled', height=20)
        self.messages_area.pack(fill=tk.BOTH, expand=True, pady=5)

        # Нижняя панель - ввод сообщения и кнопки
        bottom_frame = tk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=5)

        self.message_entry = tk.Entry(bottom_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<Return>', lambda e: self.send_message())

        # Автофокус на поле ввода при клике в любом месте окна
        self.root.bind('<FocusIn>', lambda e: self.message_entry.focus_set())
        self.messages_area.bind('<Button-1>', lambda e: self.message_entry.focus_set())

        # Устанавливаем фокус на поле ввода при открытии окна
        self.root.after(100, lambda: self.message_entry.focus_set())

        self.send_btn = tk.Button(bottom_frame, text="Отправить",
                                  command=self.send_message,
                                  bg="#0088cc", fg="white")
        self.send_btn.pack(side=tk.LEFT, padx=2)

        self.attach_btn = tk.Button(bottom_frame, text="📎 Файл",
                                    command=self.attach_file,
                                    bg="#00aa00", fg="white")
        self.attach_btn.pack(side=tk.LEFT, padx=2)

        self.edit_btn = tk.Button(bottom_frame, text="✏️ Редактировать",
                                  command=self.edit_last_message,
                                  bg="#ff9800", fg="white")
        self.edit_btn.pack(side=tk.LEFT, padx=2)

    def connect_to_telegram(self):
        # Проверяем, что все необходимые данные загружены
        if not API_ID or not API_HASH or not PHONE:
            messagebox.showerror("Ошибка",
                                 "Пожалуйста, создайте файл .env с параметрами:\n"
                                 "API_ID=ваш_api_id\n"
                                 "API_HASH=ваш_api_hash\n"
                                 "PHONE=+ваш_номер\n"
                                 "TRUSTED_CONTACTS=id1,id2,id3\n\n"
                                 "Получите API_ID и API_HASH на https://my.telegram.org")
            return

        if not TRUSTED_CONTACTS:
            messagebox.showwarning("Предупреждение",
                                   "Список TRUSTED_CONTACTS пуст!\n"
                                   "Добавьте ID контактов в .env файл:\n"
                                   "TRUSTED_CONTACTS=94361431,123456789")

        # Запускаем asyncio в отдельном потоке
        thread = threading.Thread(target=self.run_telegram_client, daemon=True)
        thread.start()

        # Настраиваем tray icon в отдельном потоке
        tray_thread = threading.Thread(target=self.setup_tray, daemon=True)
        tray_thread.start()

    def run_telegram_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start_client())

    async def start_client(self):
        try:
            logging.info(f"Создание клиента с API_ID={API_ID}, PHONE={PHONE}")
            self.client = TelegramClient('session_name', API_ID, API_HASH)

            logging.info("Подключение к Telegram...")
            await self.client.connect()
            logging.info("Подключение успешно!")

            if not await self.client.is_user_authorized():
                logging.info("Пользователь не авторизован, отправка запроса кода...")
                try:
                    logging.info(f"Отправка запроса кода на {PHONE}")
                    result = await self.client.send_code_request(PHONE, force_sms=True)
                    logging.info(f"Код отправлен! Phone code hash: {getattr(result, 'phone_code_hash', None)}")
                    self.root.after(0, lambda: messagebox.showinfo("Информация",
                                                                   "Код отправлен! Проверьте чат от 'Telegram' в приложении (или SMS)."))
                except Exception as e:
                    logging.error(f"Ошибка запроса кода: {e}")
                    self.root.after(0, lambda: messagebox.showerror("Ошибка",
                                                                    f"Не удалось отправить код: {e}\nПроверьте номер, API или флуд-лимиты."))
                    return

                self.root.after(0, self.root.deiconify)
                code = await self.get_code_from_user()
                self.root.after(0, self.root.withdraw)
                if not code:
                    raise Exception("Код не введен")

                logging.info(f"Пользователь ввел код: {code}")

                try:
                    logging.info("Попытка авторизации...")
                    await self.client.sign_in(PHONE, code)
                    logging.info("Авторизация успешна!")
                except Exception as e:
                    logging.error(f"Ошибка авторизации: {e}")
                    if 'password' in str(e).lower():
                        logging.info("Требуется 2FA пароль")
                        self.root.after(0, self.root.deiconify)
                        password = await self.get_password_from_user()
                        self.root.after(0, self.root.withdraw)
                        if not password:
                            raise Exception("Пароль не введен")
                        await self.client.sign_in(password=password)
                        logging.info("Вход с паролем успешен!")
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка авторизации: {e}"))
                        raise e
            else:
                logging.info("Пользователь уже авторизован!")

            await self.load_dialogs()

            def schedule_update():
                asyncio.run_coroutine_threadsafe(self.load_dialogs(), self.loop)
                self.loop.call_later(5, schedule_update)

            self.loop.call_later(5, schedule_update)

            @self.client.on(events.NewMessage(incoming=True))
            async def handler(event):
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
                        media_info = await self.download_media(event.message, sender_name, timestamp)
                    except Exception as e:
                        logging.error(f"Ошибка скачивания медиа: {e}")
                        media_info = "[Ошибка загрузки файла]"

                if not any(getattr(d.entity, 'id', None) == chat_id for d in self.dialogs):
                    await self.load_dialogs()

                if not self.root.winfo_viewable():
                    display_msg = f"{message} {media_info}".strip()
                    self.root.after(0, lambda sn=sender_name, dm=display_msg, ci=chat_id:
                    self.show_popup(sn, dm, ci))
                    self.play_notification_sound()
                else:
                    if self.current_chat and getattr(self.current_chat, 'id', None) == chat_id:
                        self.root.after(0, lambda: self.blink_chat_background())

                if self.current_chat and getattr(self.current_chat, 'id', None) == chat_id:
                    display_text = f"[{timestamp}] {sender_name}: {message} {media_info}".strip()
                    self.root.after(0, lambda dt=display_text: self.display_message(dt))

                self.root.after(0, lambda: self.update_unread_marks())

            @self.client.on(events.MessageEdited)
            async def edit_handler(event):
                # Обработка редактирования сообщений
                chat_id = getattr(event.chat_id, '__int__', lambda: event.chat_id)()
                if chat_id is None and event.message:
                    chat_id = getattr(event.message, 'peer_id', None)
                if chat_id not in TRUSTED_CONTACTS:
                    return

                if self.current_chat and getattr(self.current_chat, 'id', None) == chat_id:
                    # Перезагружаем сообщения для текущего чата
                    self.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                        self.load_messages(), self.loop
                    ))

            @self.client.on(events.MessageDeleted)
            async def delete_handler(event):
                # Обработка удаления сообщений
                if self.current_chat:
                    chat_id = getattr(self.current_chat, 'id', None)
                    if chat_id in TRUSTED_CONTACTS:
                        # Перезагружаем сообщения для текущего чата
                        self.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                            self.load_messages(), self.loop
                        ))

            await self.client.run_until_disconnected()

        except Exception as e:
            error_msg = str(e)
            logging.exception("Ошибка в start_client")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка подключения:\n{error_msg}"))

    async def download_media(self, message, sender_name, timestamp):
        """Скачивает медиа файл в папку media"""
        try:
            # Генерируем уникальное имя файла
            date_str = timestamp.replace(":", "-").replace(" ", "_")
            safe_sender = "".join(c for c in sender_name if c.isalnum() or c in (' ', '-', '_'))

            if message.photo:
                filename = f"{date_str}_{safe_sender}_photo.jpg"
                filepath = os.path.join(MEDIA_DIR, filename)
                await self.client.download_media(message.photo, filepath)
                return f"[📷 Фото: {filename}]"

            elif message.document:
                # Получаем оригинальное имя файла если есть
                for attr in message.document.attributes:
                    if hasattr(attr, 'file_name'):
                        original_name = attr.file_name
                        filename = f"{date_str}_{safe_sender}_{original_name}"
                        filepath = os.path.join(MEDIA_DIR, filename)
                        await self.client.download_media(message.document, filepath)
                        return f"[📄 Файл: {filename}]"

                # Если имени нет, используем ID документа
                filename = f"{date_str}_{safe_sender}_doc_{message.document.id}"
                filepath = os.path.join(MEDIA_DIR, filename)
                await self.client.download_media(message.document, filepath)
                return f"[📄 Файл: {filename}]"

            elif message.video:
                filename = f"{date_str}_{safe_sender}_video.mp4"
                filepath = os.path.join(MEDIA_DIR, filename)
                await self.client.download_media(message.video, filepath)
                return f"[🎥 Видео: {filename}]"

            elif message.voice:
                filename = f"{date_str}_{safe_sender}_voice.ogg"
                filepath = os.path.join(MEDIA_DIR, filename)
                await self.client.download_media(message.voice, filepath)
                return f"[🎤 Голосовое: {filename}]"

            elif message.audio:
                filename = f"{date_str}_{safe_sender}_audio.mp3"
                filepath = os.path.join(MEDIA_DIR, filename)
                await self.client.download_media(message.audio, filepath)
                return f"[🎵 Аудио: {filename}]"

            else:
                return "[📎 Медиа]"

        except Exception as e:
            logging.error(f"Ошибка загрузки медиа: {e}")
            return "[Ошибка загрузки]"

    async def get_code_from_user(self):
        code_container = [None]

        def ask_code():
            code = simpledialog.askstring(
                "Код подтверждения",
                f"Введите код, отправленный в Telegram на номер {PHONE}:",
                parent=self.root
            )
            code_container[0] = code

        self.root.after(0, ask_code)

        while code_container[0] is None:
            await asyncio.sleep(0.1)

        return code_container[0]

    async def get_password_from_user(self):
        password_container = [None]

        def ask_password():
            password = simpledialog.askstring(
                "Двухфакторная аутентификация",
                "Введите пароль облачной аутентификации:",
                parent=self.root,
                show='*'
            )
            password_container[0] = password

        self.root.after(0, ask_password)

        while password_container[0] is None:
            await asyncio.sleep(0.1)

        return password_container[0]

    async def load_dialogs(self):
        all_dialogs = await self.client.get_dialogs(limit=50)
        self.dialogs = [d for d in all_dialogs if getattr(d.entity, 'id', None) in TRUSTED_CONTACTS]
        self.root.after(0, lambda: self.chat_listbox.delete(0, tk.END))

        for dialog in self.dialogs:
            unread = getattr(dialog, 'unread_count', 0)
            name = getattr(dialog, 'name', None) or getattr(dialog.entity, 'title',
                                                            str(getattr(dialog.entity, 'id', '')))
            display_name = ("* " if unread > 0 else "") + name
            self.root.after(0, lambda n=display_name: self.chat_listbox.insert(tk.END, n))

    def update_unread_marks(self):
        self.chat_listbox.delete(0, tk.END)
        for dialog in self.dialogs:
            unread = getattr(dialog, 'unread_count', 0)
            name = getattr(dialog, 'name', None) or getattr(dialog.entity, 'title',
                                                            str(getattr(dialog.entity, 'id', '')))
            display_name = ("* " if unread > 0 else "") + name
            self.chat_listbox.insert(tk.END, display_name)

    def on_chat_select(self, event):
        selection = self.chat_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        self.current_chat = self.dialogs[index]

        if self.loop:
            asyncio.run_coroutine_threadsafe(self.load_messages(), self.loop)

    async def load_messages(self):
        self.root.after(0, lambda: self.messages_area.config(state='normal'))
        self.root.after(0, lambda: self.messages_area.delete(1.0, tk.END))

        # Очищаем словарь сообщений
        self.messages_dict.clear()

        msgs = await self.client.get_messages(self.current_chat, limit=50)
        for msg in reversed(msgs):
            if getattr(msg, 'message', None) or getattr(msg, 'media', None):
                # Сохраняем сообщение в словарь
                msg_id = getattr(msg, 'id', None)
                if msg_id:
                    self.messages_dict[msg_id] = msg

                sender_name = "Я" if getattr(msg, 'out', False) else (
                    getattr(getattr(msg, 'sender', None), 'first_name', 'Unknown') if getattr(msg, 'sender',
                                                                                              None) else 'Unknown')
                timestamp = msg.date.strftime("%Y-%m-%d %H:%M:%S") if getattr(msg, 'date', None) else ''

                message_text = getattr(msg, 'message', '')
                media_info = ""

                # Добавляем метку "(ред.)" если сообщение отредактировано
                edited_mark = " (ред.)" if getattr(msg, 'edit_date', None) else ""

                # Показываем информацию о медиа в истории
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

    def display_message(self, message):
        self.messages_area.config(state='normal')
        self.messages_area.insert(tk.END, message + "\n")
        self.messages_area.see(tk.END)
        self.messages_area.config(state='disabled')

    def send_message(self):
        if not self.client or not self.current_chat:
            messagebox.showwarning("Предупреждение", "Выберите чат!")
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        self.message_entry.delete(0, tk.END)

        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.send_message_async(message),
                self.loop
            )

    async def send_message_async(self, message):
        try:
            sent_msg = await self.client.send_message(self.current_chat, message)
            # Сохраняем ID последнего отправленного сообщения
            self.last_message_id = getattr(sent_msg, 'id', None)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.display_message(f"[{timestamp}] Я: {message}"))
        except Exception as e:
            logging.exception("Ошибка отправки сообщения")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка отправки: {e}"))

    def attach_file(self):
        """Открывает диалог выбора файла и отправляет его"""
        if not self.client or not self.current_chat:
            messagebox.showwarning("Предупреждение", "Выберите чат!")
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

        if filepath:
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.send_file_async(filepath),
                    self.loop
                )

    async def send_file_async(self, filepath):
        """Отправляет файл в текущий чат"""
        try:
            filename = os.path.basename(filepath)
            self.root.after(0, lambda: self.display_message(f"[Отправка файла: {filename}...]"))

            await self.client.send_file(self.current_chat, filepath)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.display_message(f"[{timestamp}] Я: [📎 Отправлен файл: {filename}]"))
        except Exception as e:
            logging.exception("Ошибка отправки файла")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка отправки файла: {e}"))

    def edit_last_message(self):
        """Редактирует последнее отправленное сообщение"""
        if not self.client or not self.current_chat:
            messagebox.showwarning("Предупреждение", "Выберите чат!")
            return

        if not self.last_message_id:
            messagebox.showwarning("Предупреждение", "Нет сообщений для редактирования!")
            return

        # Получаем новый текст сообщения
        new_text = simpledialog.askstring(
            "Редактировать сообщение",
            "Введите новый текст сообщения:",
            parent=self.root
        )

        if new_text and new_text.strip():
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.edit_message_async(self.last_message_id, new_text.strip()),
                    self.loop
                )

    async def edit_message_async(self, message_id, new_text):
        """Редактирует сообщение асинхронно"""
        try:
            await self.client.edit_message(self.current_chat, message_id, new_text)
            # Перезагружаем историю сообщений
            self.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                self.load_messages(), self.loop
            ))
            self.root.after(0, lambda: messagebox.showinfo("Успех", "Сообщение отредактировано!"))
        except Exception as e:
            logging.exception("Ошибка редактирования сообщения")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка редактирования: {e}"))

    def play_notification_sound(self):
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 500)
            except Exception:
                pass

    def show_popup(self, sender_name, message, chat_id):
        # Закрываем все предыдущие popup окна
        self.close_all_popups()

        popup = tk.Toplevel(self.root)

        # Убираем стандартные кнопки окна (minimize, maximize, close)
        popup.overrideredirect(True)

        # Вычисляем необходимый размер окна в зависимости от длины сообщения
        base_width = 350
        base_height = 180

        # Увеличиваем высоту для длинных сообщений
        message_length = len(message)
        if message_length > 100:
            extra_height = min((message_length - 100) // 2, 200)  # Максимум +200px
            base_height += extra_height

        # Увеличиваем ширину для очень длинных строк
        if message_length > 200:
            base_width = 450

        popup.attributes('-topmost', True)

        # Центрируем окно
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width / 2) - (base_width / 2)
        y = (screen_height / 2) - (base_height / 2)
        popup.geometry(f"{base_width}x{base_height}+{int(x)}+{int(y)}")

        # Добавляем рамку и фон
        popup.configure(bg='#f0f0f0', highlightthickness=3, highlightbackground='#0088cc')

        # Создаем фрейм для содержимого с отступами
        content_frame = tk.Frame(popup, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Заголовок "от:"
        tk.Label(content_frame, text=f"от: {sender_name}",
                 bg='#f0f0f0', font=("Arial", 11)).pack(anchor='w', pady=(0, 10))

        # Создаем фрейм с прокруткой для сообщения
        message_frame = tk.Frame(content_frame, bg='#f0f0f0')
        message_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Если сообщение длинное, добавляем scrollbar
        if message_length > 150:
            scrollbar = tk.Scrollbar(message_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            message_text = tk.Text(message_frame, wrap=tk.WORD,
                                   bg='#f0f0f0',
                                   font=("Arial", 14, "bold italic"),
                                   relief=tk.FLAT,
                                   yscrollcommand=scrollbar.set,
                                   height=8)
            message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            message_text.insert(1.0, f"✉ {message}")
            message_text.config(state='disabled')
            scrollbar.config(command=message_text.yview)
        else:
            # Для коротких сообщений используем Label
            message_label = tk.Label(message_frame, text=f"✉ {message}",
                                     wraplength=base_width - 60,
                                     bg='#f0f0f0',
                                     font=("Arial", 14, "bold italic"),
                                     justify=tk.LEFT)
            message_label.pack(fill=tk.BOTH, expand=True)

        # Фрейм для кнопок - ВАЖНО: НЕ expand=True
        button_frame = tk.Frame(content_frame, bg='#f0f0f0')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))

        def reply():
            popup.destroy()
            self.remove_popup(popup)
            self.toggle_window()
            for i, d in enumerate(self.dialogs):
                if getattr(d.entity, 'id', None) == chat_id:
                    self.chat_listbox.select_set(i)
                    self.on_chat_select(None)
                    self.blink_chat_name(i)
                    break

        def close():
            popup.destroy()
            self.remove_popup(popup)
            if self.loop:
                # Обрезаем сообщение если оно слишком длинное
                short_message = message[:50] + "..." if len(message) > 50 else message
                reply_text = f"Пользователь закрыл уведомление на сообщение: \"{short_message}\""
                asyncio.run_coroutine_threadsafe(
                    self.client.send_message(chat_id, reply_text),
                    self.loop
                )

        tk.Button(button_frame, text="Ответить", command=reply,
                  bg="#0088cc", fg="white", font=("Arial", 11, "bold"),
                  padx=20, pady=8, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=8)
        tk.Button(button_frame, text="Закрыть", command=close,
                  bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
                  padx=20, pady=8, relief=tk.FLAT, cursor="hand2").pack(side=tk.RIGHT, padx=8)

        # Добавляем popup в список активных
        self.active_popups.append(popup)

    def close_all_popups(self):
        """Закрывает все активные popup окна"""
        for popup in self.active_popups[:]:  # Копируем список для безопасной итерации
            try:
                popup.destroy()
            except:
                pass
        self.active_popups.clear()

    def remove_popup(self, popup):
        """Удаляет popup из списка активных"""
        if popup in self.active_popups:
            self.active_popups.remove(popup)

    def blink_chat_name(self, index):
        def blink(count=5, delay=300):
            if count == 0:
                self.chat_listbox.itemconfig(index, {'fg': 'black'})
                return
            color = 'green' if count % 2 == 1 else 'black'
            self.chat_listbox.itemconfig(index, {'fg': color})
            self.root.after(delay, lambda: blink(count - 1, delay))

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
        """Создаёт иконку в трее с обработкой левого клика"""
        size = 64
        # Синий квадрат (Telegram blue)
        image = Image.new('RGB', (size, size), color=(0, 136, 204))

        draw = ImageDraw.Draw(image)

        # Исходные координаты "самолётика"
        plane = [
            (size * 0.25, size * 0.75),  # хвост
            (size * 0.80, size * 0.55),  # нос
            (size * 0.35, size * 0.25)  # верхняя точка крыла
        ]

        # Разворот на 180°: отражаем относительно центра
        rotated = [(size - x, size - y) for (x, y) in plane]

        # Рисуем белый треугольник
        draw.polygon(rotated, fill="white")

        # Прорезь в хвосте — синяя линия до половины треугольника
        tail_start = (size * 0.25, size * 0.75)  # хвост
        tail_end = (size * 0.575, size * 0.450)  # примерно середина медианы квадрата
        draw.line([tail_start, tail_end], fill=(0, 136, 204), width=int(size * 0.08))

        def on_left_click(icon, item):
            """Обработка левого клика - сворачивание/разворачивание окна"""
            self.root.after(0, self.toggle_window)

        def on_quit(icon, item):
            """Выход из приложения"""
            self.quit_app()

        # Меню трея
        menu = pystray.Menu(
            pystray.MenuItem('Открыть/Свернуть', on_left_click, default=True),
            pystray.MenuItem('Выход', on_quit)
        )

        self.tray_icon = pystray.Icon('telegram_client', image, 'Telegram Client', menu)

        try:
            self.tray_icon.run()
        except Exception:
            logging.exception("Ошибка запуска трей-иконки")

    def toggle_window(self):
        """Переключает видимость главного окна"""
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.lift()  # Поднимаем окно наверх
            self.root.focus_force()  # Даём фокус окну
            self.message_entry.focus_set()  # Устанавливаем фокус на поле ввода

    def minimize_to_tray(self):
        """Сворачивает окно в трей"""
        self.root.withdraw()

    def on_unmap(self, event):
        """Обработка минимизации окна"""
        if self.root.state() == 'iconic':
            self.root.withdraw()

    def quit_app(self):
        """Полное закрытие приложения"""
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        if self.client and self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramGUI(root)
    root.mainloop()