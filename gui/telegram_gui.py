import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import asyncio
import threading
import datetime
import platform
import os
import logging
import re
import subprocess
import webbrowser

from config.settings import API_ID, API_HASH, PHONE, TRUSTED_CONTACTS, WINDOW_WIDTH, WINDOW_HEIGHT
from client.telegram_client import TelegramClientManager
from telethon.errors import MessageEditTimeExpiredError
from utils.media import describe_media, download_media
from utils.app_icon import set_window_icon
from utils.tray import create_tray_icon
from gui.widgets import create_chat_list, create_message_area, create_input_panel, create_status_bar
from gui.popup import create_popup


URL_PATTERN = re.compile(r"(?:(?:https?://)|(?:www\.))[\w\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


class TelegramGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Client")
        set_window_icon(self.root)

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
        self.blink_timers = {}
        self.message_blocks = []
        self.selected_message_id = None
        self.selected_message_outgoing = False
        self.context_message_block = None
        self.context_link_target = None
        self.context_email_target = None
        self.hover_tag_active = None
        self.current_status_text = ""
        self.current_status_level = "neutral"
        self.is_closing = False  # Для хранения таймеров мигания

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.bind("<Unmap>", self.on_unmap)
        self.connect_to_telegram()

    def create_widgets(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.chat_listbox = create_chat_list(main_frame)
        self.chat_listbox.bind('<<ListboxSelect>>', self.on_chat_select)

        right_frame, self.chat_header_label, self.messages_area = create_message_area(main_frame)
        self.setup_message_copy()
        self.setup_global_shortcuts()

        callbacks = {
            'send': self.send_message,
            'attach': self.attach_file,
            'edit': self.edit_last_message
        }
        self.message_entry = create_input_panel(right_frame, callbacks)
        _, self.status_dot, self.status_label = create_status_bar(self.root)

        # ЗАМЕНЕНО: "\u0417\u0430\u043f\u0443\u0441\u043a..." -> "Запуск..."
        self.set_status("Запуск...", "neutral")

        # Автофокус
        self.root.after(100, lambda: self.message_entry.focus_set())

    def setup_message_copy(self):
        self.configure_message_tags()

        self.message_context_menu = tk.Menu(self.messages_area, tearoff=0)
        self.message_context_menu.add_command(label="Копировать", command=self.copy_selected_messages)
        self.message_context_menu.add_command(label="Копировать всё", command=self.copy_all_messages)
        self.message_context_menu.add_command(label="Выделить всё", command=self.select_all_messages)
        self.message_context_menu.add_separator()
        self.message_context_menu.add_command(label="Открыть файл", command=self.open_selected_media)
        self.message_context_menu.add_command(label="Открыть папку с файлом", command=self.open_selected_media_folder)
        self.message_context_menu.add_separator()
        self.message_context_menu.add_command(label="Копировать ссылку", command=self.copy_context_link)
        self.message_context_menu.add_command(label="Копировать адрес", command=self.copy_context_email)
        self.open_file_menu_index = 4
        self.open_folder_menu_index = 5
        self.copy_link_menu_index = 7
        self.copy_email_menu_index = 8

        self.messages_area.bind("<Control-c>", self.copy_selected_messages_event)
        self.messages_area.bind("<Control-C>", self.copy_selected_messages_event)
        self.messages_area.bind("<Control-a>", self.select_all_messages)
        self.messages_area.bind("<Control-A>", self.select_all_messages)
        self.messages_area.bind("<Button-3>", self.show_message_context_menu)
        self.messages_area.bind("<Motion>", self.update_hover_state, add="+")
        self.messages_area.bind("<Leave>", self.clear_hover_state, add="+")
        self.messages_area.bind("<ButtonRelease-1>", self.on_message_area_click, add="+")
        self.messages_area.bind("<KeyPress>", self.prevent_messages_area_edit)
        self.messages_area.bind("<<Cut>>", lambda event: "break")
        self.messages_area.bind("<<Paste>>", lambda event: "break")
        self.messages_area.bind("<<Clear>>", lambda event: "break")

    def setup_global_shortcuts(self):
        self.root.bind_all("<Control-c>", self.handle_global_copy, add="+")
        self.root.bind_all("<Control-C>", self.handle_global_copy, add="+")
        self.root.bind_all("<Control-v>", self.handle_global_paste, add="+")
        self.root.bind_all("<Control-V>", self.handle_global_paste, add="+")
        self.root.bind_all("<Control-x>", self.handle_global_cut, add="+")
        self.root.bind_all("<Control-X>", self.handle_global_cut, add="+")
        self.root.bind_all("<Control-a>", self.handle_global_select_all, add="+")
        self.root.bind_all("<Control-A>", self.handle_global_select_all, add="+")

    def handle_global_copy(self, event=None):
        widget = self.root.focus_get()
        if widget == self.messages_area:
            return self.copy_selected_messages_event(event)
        if widget == self.message_entry:
            self.message_entry.event_generate("<<Copy>>")
            return "break"
        return None

    def handle_global_paste(self, event=None):
        widget = self.root.focus_get()
        if widget == self.message_entry:
            self.message_entry.event_generate("<<Paste>>")
            return "break"
        return None

    def handle_global_cut(self, event=None):
        widget = self.root.focus_get()
        if widget == self.message_entry:
            self.message_entry.event_generate("<<Cut>>")
            return "break"
        return None

    def handle_global_select_all(self, event=None):
        widget = self.root.focus_get()
        if widget == self.messages_area:
            return self.select_all_messages(event)
        if widget == self.message_entry:
            self.message_entry.focus_set()
            self.message_entry.select_range(0, tk.END)
            self.message_entry.icursor(tk.END)
            return "break"
        return None

    def configure_message_tags(self):
        self.messages_area.tag_configure(
            "sel",
            background="#bcdcff",
            foreground="#102030",
        )
        self.messages_area.tag_configure(
            "message_in_meta",
            foreground="#5c6f7e",
            font=("Segoe UI", 9, "bold"),
            lmargin1=14,
            lmargin2=14,
            rmargin=110,
            spacing1=8,
        )
        self.messages_area.tag_configure(
            "message_in_body",
            background="#f4f8fb",
            foreground="#1e2a33",
            font=("Segoe UI", 11),
            lmargin1=14,
            lmargin2=14,
            rmargin=110,
            spacing3=10,
        )
        self.messages_area.tag_configure(
            "message_in_body_media",
            background="#f4f8fb",
            foreground="#0b63b6",
            font=("Segoe UI", 11, "underline"),
            lmargin1=14,
            lmargin2=14,
            rmargin=110,
            spacing3=10,
        )
        self.messages_area.tag_configure(
            "message_out_meta",
            foreground="#3d608d",
            font=("Segoe UI", 9, "bold"),
            lmargin1=110,
            lmargin2=110,
            rmargin=14,
            justify="right",
            spacing1=8,
        )
        self.messages_area.tag_configure(
            "message_out_body",
            background="#e9f3ff",
            foreground="#173252",
            font=("Segoe UI", 11),
            lmargin1=110,
            lmargin2=110,
            rmargin=14,
            justify="right",
            spacing3=10,
        )
        self.messages_area.tag_configure(
            "message_out_body_media",
            background="#e9f3ff",
            foreground="#0a58a8",
            font=("Segoe UI", 11, "underline"),
            lmargin1=110,
            lmargin2=110,
            rmargin=14,
            justify="right",
            spacing3=10,
        )
        self.messages_area.tag_configure(
            "message_selected",
            background="#dcecff",
            foreground="#102030",
        )
        self.messages_area.tag_configure(
            "message_link",
            foreground="#0b63b6",
            underline=1,
        )
        self.messages_area.tag_configure(
            "message_email",
            foreground="#0b63b6",
            underline=1,
        )
        self.messages_area.tag_configure(
            "message_hover",
            foreground="#0050c8",
            underline=1,
        )
        self.messages_area.tag_configure(
            "message_system",
            foreground="#5f6b76",
            font=("Consolas", 10),
            lmargin1=12,
            lmargin2=12,
            rmargin=12,
            spacing1=4,
            spacing3=6,
        )
        self.messages_area.tag_raise("message_link")
        self.messages_area.tag_raise("message_email")
        self.messages_area.tag_raise("message_hover")
        self.messages_area.tag_raise("sel")

    def append_chat_message_to_area(self, sender_name, timestamp, message_text, outgoing=False, edited=False, message_id=None, media_path=None):
        safe_sender = (sender_name or "Unknown").strip() or "Unknown"
        safe_body = (message_text or "").strip() or "-"
        edited_suffix = "  · ред." if edited else ""
        meta_text = f"{safe_sender}  {timestamp}{edited_suffix}".strip()
        meta_tag = "message_out_meta" if outgoing else "message_in_meta"
        body_tag = "message_out_body" if outgoing else "message_in_body"

        self.set_messages_area_state('normal')
        if self.messages_area.index('end-1c') != '1.0':
            self.messages_area.insert(tk.END, "\n")
        meta_start = self.messages_area.index(tk.END)
        self.messages_area.insert(tk.END, meta_text + "\n", (meta_tag,))
        meta_end = self.messages_area.index(tk.END)
        body_start = self.messages_area.index(tk.END)
        self.messages_area.insert(tk.END, safe_body + "\n", (body_tag,))
        body_end = self.messages_area.index(tk.END)
        self.apply_interactive_tags(body_start, safe_body, media_path)
        if message_id is not None:
            self.message_blocks.append({
                "message_id": message_id,
                "outgoing": outgoing,
                "meta_start": meta_start,
                "meta_end": meta_end,
                "body_start": body_start,
                "body_end": body_end,
                "media_path": media_path,
            })
        self.messages_area.see(tk.END)
        self.set_messages_area_state('disabled')

    def apply_interactive_tags(self, body_start, body_text, media_path=None):
        for match in URL_PATTERN.finditer(body_text):
            start_index = f"{body_start}+{match.start()}c"
            end_index = f"{body_start}+{match.end()}c"
            self.messages_area.tag_add("message_link", start_index, end_index)
        for match in EMAIL_PATTERN.finditer(body_text):
            start_index = f"{body_start}+{match.start()}c"
            end_index = f"{body_start}+{match.end()}c"
            self.messages_area.tag_add("message_email", start_index, end_index)
        if media_path:
            media_match = re.search(r"\[[^\]]+\]$", body_text)
            if media_match:
                start_index = f"{body_start}+{media_match.start()}c"
                end_index = f"{body_start}+{media_match.end()}c"
                self.messages_area.tag_add("message_link", start_index, end_index)

    def set_messages_area_state(self, state):
        self.messages_area.configure(state='normal')

    def prevent_messages_area_edit(self, event):
        allowed_navigation = {
            "Left", "Right", "Up", "Down", "Home", "End",
            "Prior", "Next", "Shift_L", "Shift_R", "Control_L", "Control_R",
        }
        if event.keysym in allowed_navigation:
            return None
        if (event.state & 0x4) and event.keysym.lower() in {"c", "a"}:
            return None
        return "break"

    def find_message_block_by_index(self, index):
        for block in reversed(self.message_blocks):
            if self.messages_area.compare(index, ">=", block["meta_start"]) and self.messages_area.compare(index, "<", block["body_end"]):
                return block
        return None

    def highlight_selected_message(self):
        self.messages_area.tag_remove("message_selected", "1.0", tk.END)
        if self.selected_message_id is None:
            return
        for block in self.message_blocks:
            if block["message_id"] == self.selected_message_id:
                self.messages_area.tag_add("message_selected", block["meta_start"], block["body_end"])
                self.messages_area.tag_raise("sel")
                return

    def update_hover_state(self, event):
        try:
            hover_index = self.messages_area.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None
        line, column = hover_index.split('.')
        column = int(column)
        line_text = self.messages_area.get(f"{line}.0", f"{line}.end")

        for pattern, tag_name in ((URL_PATTERN, "message_link"), (EMAIL_PATTERN, "message_email")):
            for match in pattern.finditer(line_text):
                if match.start() <= column < match.end():
                    start_index = f"{line}.0+{match.start()}c"
                    end_index = f"{line}.0+{match.end()}c"
                    self.messages_area.tag_remove("message_hover", "1.0", tk.END)
                    self.messages_area.tag_add("message_hover", start_index, end_index)
                    self.hover_tag_active = tag_name
                    self.messages_area.config(cursor="hand2")
                    return None

        media_match = re.search(r"\[[^\]]+\]$", line_text)
        if media_match and media_match.start() <= column < media_match.end():
            start_index = f"{line}.0+{media_match.start()}c"
            end_index = f"{line}.0+{media_match.end()}c"
            self.messages_area.tag_remove("message_hover", "1.0", tk.END)
            self.messages_area.tag_add("message_hover", start_index, end_index)
            self.hover_tag_active = "message_link"
            self.messages_area.config(cursor="hand2")
            return None

        self.clear_hover_state()
        return None

    def clear_hover_state(self, event=None):
        self.hover_tag_active = None
        self.messages_area.tag_remove("message_hover", "1.0", tk.END)
        self.messages_area.config(cursor="xterm")
        return None

    def on_message_area_click(self, event):
        try:
            click_index = self.messages_area.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None

        link_target = self.get_line_target(click_index, URL_PATTERN)
        if link_target:
            self.open_context_link(link_target)
            return "break"

        email_target = self.get_line_target(click_index, EMAIL_PATTERN)
        if email_target:
            self.context_email_target = email_target
            self.copy_context_email()
            return "break"

        media_block = self.get_media_block_for_index(click_index)
        if media_block:
            self.context_message_block = media_block
            self.open_selected_media()
            return "break"

        block = self.find_message_block_by_index(click_index)
        if not block or not block["outgoing"]:
            self.selected_message_id = None
            self.selected_message_outgoing = False
            self.highlight_selected_message()
            return None
        self.selected_message_id = block["message_id"]
        self.selected_message_outgoing = True
        self.last_message_id = block["message_id"]
        self.highlight_selected_message()
        self.set_status("Выбрано сообщение для редактирования", "neutral")
        return None

    def clear_messages_area(self):
        self.set_messages_area_state('normal')
        self.messages_area.delete('1.0', tk.END)
        self.set_messages_area_state('disabled')

    def append_message_to_area(self, message):
        self.set_messages_area_state('normal')
        self.messages_area.insert(tk.END, message + "\n", ("message_system",))
        self.messages_area.see(tk.END)
        self.set_messages_area_state('disabled')

    def replace_messages_area_content(self, lines):
        self.set_messages_area_state('normal')
        self.messages_area.delete('1.0', tk.END)
        if lines:
            self.messages_area.insert('1.0', '\n'.join(lines) + '\n')
        self.messages_area.see(tk.END)
        self.set_messages_area_state('disabled')

    def copy_selected_messages(self):
        try:
            selected_text = self.messages_area.get("sel.first", "sel.last")
        except tk.TclError:
            return
        cleaned_lines = []

        # ЗАМЕНЕНО: \u00b7 -> · (точка-разделитель) и \u0440\u0435\u0434\. -> ред.
        header_pattern = re.compile(
            r"^.+\s{2}\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\s+·\s+ред\.)?$"
        )
        for line in selected_text.splitlines():
            if header_pattern.match(line.strip()):
                continue
            cleaned_lines.append(line)
        selected_text = "\n".join(cleaned_lines).strip("\n")
        if not selected_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(selected_text)

    def copy_selected_messages_event(self, event=None):
        self.copy_selected_messages()
        return "break"

    def copy_all_messages(self):
        full_text = self.messages_area.get("1.0", "end-1c")
        if not full_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(full_text)

    def select_all_messages(self, event=None):
        self.messages_area.focus_set()
        self.messages_area.tag_add(tk.SEL, "1.0", "end-1c")
        self.messages_area.mark_set(tk.INSERT, "1.0")
        self.messages_area.see(tk.INSERT)
        return "break"

    def get_line_target(self, index, pattern):
        if not index:
            return None
        line, column = index.split('.')
        column = int(column)
        line_text = self.messages_area.get(f"{line}.0", f"{line}.end")
        for match in pattern.finditer(line_text):
            if match.start() <= column < match.end():
                return match.group(0).rstrip(').,;]')
        return None

    def copy_context_link(self):
        if not self.context_link_target:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.context_link_target)
        self.show_brief_status("Скопировано!", "neutral")

    def copy_context_email(self):
        if not self.context_email_target:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.context_email_target)
        self.show_brief_status("Скопировано!", "neutral")

    def open_context_link(self, url):
        if not url:
            return
        target = url if re.match(r"^https?://", url, re.IGNORECASE) else f"https://{url}"
        webbrowser.open(target)
        self.show_brief_status("Ссылка открыта", "neutral", duration_ms=350, restore_text="Подключен", restore_level="online")

    def show_message_context_menu(self, event):
        self.messages_area.focus_set()
        try:
            click_index = self.messages_area.index(f"@{event.x},{event.y}")
        except tk.TclError:
            click_index = None
        self.context_message_block = self.get_media_block_for_index(click_index) if click_index else None
        self.context_link_target = self.get_line_target(click_index, URL_PATTERN) if click_index else None
        self.context_email_target = self.get_line_target(click_index, EMAIL_PATTERN) if click_index else None
        media_state = tk.NORMAL if self.context_message_block else tk.DISABLED
        link_state = tk.NORMAL if self.context_link_target else tk.DISABLED
        email_state = tk.NORMAL if self.context_email_target else tk.DISABLED
        self.message_context_menu.entryconfigure(self.open_file_menu_index, state=media_state)
        self.message_context_menu.entryconfigure(self.open_folder_menu_index, state=media_state)
        self.message_context_menu.entryconfigure(self.copy_link_menu_index, state=link_state)
        self.message_context_menu.entryconfigure(self.copy_email_menu_index, state=email_state)
        self.message_context_menu.tk_popup(event.x_root, event.y_root)

    def get_media_block_for_index(self, index):
        block = self.find_message_block_by_index(index)
        if block and block.get("media_path"):
            return block
        return None

    async def download_media_for_block(self, block):
        message_id = block.get("message_id")
        message = self.messages_dict.get(message_id)
        if not message:
            self.root.after(0, lambda: self.show_warning("Не удалось найти сообщение с файлом."))
            return None
        sender_name = "Я" if block.get("outgoing") else (
            getattr(getattr(message, "sender", None), "first_name", "Unknown")
            if getattr(message, "sender", None) else "Unknown"
        )
        timestamp = message.date.strftime("%Y-%m-%d %H:%M:%S") if getattr(message, "date", None) else ""
        self.set_status("Скачивание файла...", "busy")
        media_result = await download_media(self.client, message, sender_name, timestamp)
        media_path = media_result.get("path")
        if not media_path or not os.path.exists(media_path):
            self.set_status("Ошибка скачивания файла", "error")
            self.root.after(0, lambda: self.show_error("Не удалось скачать файл из сообщения."))
            return None
        block["media_path"] = media_path
        return media_path

    def _open_media_path(self, media_path):
        try:
            os.startfile(media_path)
            self.show_brief_status("Открыт файл из чата", "neutral", duration_ms=350, restore_text="Подключен", restore_level="online")
        except OSError as e:
            self.show_error(f"Не удалось открыть файл: {e}")

    def _open_media_folder_path(self, media_path):
        try:
            subprocess.Popen(["explorer", "/select,", media_path])
            self.show_brief_status("Открыта папка с файлом", "neutral", duration_ms=350, restore_text="Подключен", restore_level="online")
        except OSError as e:
            self.show_error(f"Не удалось открыть папку: {e}")

    def open_selected_media(self):
        block = self.context_message_block or next((b for b in self.message_blocks if b.get("message_id") == self.selected_message_id), None)
        if not block:
            self.show_warning("В этом сообщении нет файла.")
            return
        media_path = block.get("media_path")
        if media_path:
            media_path = os.path.abspath(media_path)
        if media_path and os.path.exists(media_path):
            self._open_media_path(media_path)
            return
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self.download_media_for_block(block), self.loop)
            def done_callback(fut):
                try:
                    downloaded_path = fut.result()
                except Exception as e:
                    self.root.after(0, lambda err=e: self.show_error(f"Не удалось скачать файл: {err}"))
                    return
                if downloaded_path:
                    self.root.after(0, lambda p=downloaded_path: self._open_media_path(os.path.abspath(p)))
            future.add_done_callback(done_callback)
            return
        self.show_warning("Не удалось скачать файл из сообщения.")

    def open_selected_media_folder(self):
        block = self.context_message_block or next((b for b in self.message_blocks if b.get("message_id") == self.selected_message_id), None)
        if not block:
            self.show_warning("В этом сообщении нет файла.")
            return
        media_path = block.get("media_path")
        if media_path:
            media_path = os.path.abspath(media_path)
        if media_path and os.path.exists(media_path):
            self._open_media_folder_path(media_path)
            return
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(self.download_media_for_block(block), self.loop)
            def done_callback(fut):
                try:
                    downloaded_path = fut.result()
                except Exception as e:
                    self.root.after(0, lambda err=e: self.show_error(f"Не удалось скачать файл: {err}"))
                    return
                if downloaded_path:
                    self.root.after(0, lambda p=downloaded_path: self._open_media_folder_path(os.path.abspath(p)))
            future.add_done_callback(done_callback)
            return
        self.show_warning("Не удалось открыть папку с файлом.")

    def show_brief_status(self, text, level="neutral", duration_ms=450, restore_text=None, restore_level=None):
        previous_text = restore_text or self.current_status_text or "Подключен"
        previous_level = restore_level or self.current_status_level or "online"
        self.set_status(text, level)
        self.root.after(
            duration_ms,
            lambda prev_text=previous_text, prev_level=previous_level:
            self.set_status(prev_text, prev_level) if not self.is_closing else None,
        )

    def set_status(self, text, level="neutral"):
        if self.is_closing:
            return
        self.root.after(0, lambda: self._apply_status(text, level))

    def _apply_status(self, text, level):
        self.current_status_text = text
        self.current_status_level = level
        palette = {
            "neutral": ("#6c7a86", "#2f3b45", "#eef3f7"),
            "connecting": ("#d48806", "#5f3b00", "#fff7e6"),
            "online": ("#2f9e44", "#1f5130", "#edf9f0"),
            "warning": ("#e67700", "#663c00", "#fff4e6"),
            "error": ("#e03131", "#5c1f1f", "#fff0f0"),
            "busy": ("#1971c2", "#163b65", "#edf4ff"),
        }
        dot_color, text_color, bg_color = palette.get(level, palette["neutral"])
        self.status_dot.config(fg=dot_color, bg=bg_color)
        self.status_label.config(text=text, fg=text_color, bg=bg_color)
        self.status_dot.master.config(bg=bg_color)

    def connect_to_telegram(self):
        if not API_ID or not API_HASH or not PHONE:
            self.set_status("\u041d\u0435 \u0437\u0430\u0434\u0430\u043d\u044b API_ID/API_HASH/PHONE", "error")
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

    def update_chat_header(self, chat=None):
        active_chat = chat or self.current_chat
        if not active_chat:
            self.chat_header_label.config(text="История сообщений:")
            return
        chat_name = getattr(active_chat, "name", None) or getattr(
            getattr(active_chat, "entity", None),
            "title",
            str(getattr(getattr(active_chat, "entity", None), "id", "")),
        )
        self.chat_header_label.config(text=f"Чат с {chat_name}")

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

        self.root.after(0, self.apply_chat_list_highlight)
        if self.dialogs and not self.current_chat:
            self.root.after(0, self.select_first_chat)

    def select_first_chat(self):
        if not self.dialogs or self.current_chat:
            return
        self.chat_listbox.selection_clear(0, tk.END)
        self.chat_listbox.select_set(0)
        self.chat_listbox.activate(0)
        self.on_chat_select(None)

    def apply_chat_list_highlight(self):
        current_chat_id = getattr(getattr(self.current_chat, "entity", self.current_chat), "id", None)
        for index, dialog in enumerate(self.dialogs):
            dialog_id = getattr(dialog.entity, "id", None)
            if dialog_id == current_chat_id:
                self.chat_listbox.itemconfig(index, bg="#d9ecff", fg="#12314d", selectbackground="#c3e0ff", selectforeground="#0f2b45")
            else:
                self.chat_listbox.itemconfig(index, bg="white", fg="#1f2a33", selectbackground="#d9ecff", selectforeground="#12314d")

    def update_unread_marks(self):
        self.chat_listbox.delete(0, tk.END)
        for dialog in self.dialogs:
            unread = getattr(dialog, 'unread_count', 0)
            name = getattr(dialog, 'name', None) or getattr(
                dialog.entity, 'title', str(getattr(dialog.entity, 'id', ''))
            )
            display_name = ("* " if unread > 0 else "") + name
            self.chat_listbox.insert(tk.END, display_name)
        self.apply_chat_list_highlight()

    def on_chat_select(self, event):
        selection = self.chat_listbox.curselection()
        if not selection:
            return

        self.current_chat = self.dialogs[selection[0]]
        self.apply_chat_list_highlight()
        self.update_chat_header()

        if self.loop:
            asyncio.run_coroutine_threadsafe(self.load_messages(), self.loop)
            asyncio.run_coroutine_threadsafe(self.mark_as_read(), self.loop)

    async def load_messages(self):
        self.root.after(0, self.clear_messages_area)
        self.messages_dict.clear()
        self.message_blocks = []
        self.selected_message_id = None
        self.selected_message_outgoing = False

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

                media_info = ""
                media_path = None
                if msg.media:
                    media_result = describe_media(msg, sender_name, timestamp)
                    media_info = media_result.get("text", "")
                    media_path = media_result.get("path")

                body_text = f"{message_text} {media_info}".strip()
                is_outgoing = bool(getattr(msg, 'out', False))
                is_edited = bool(getattr(msg, 'edit_date', None))
                self.root.after(
                    0,
                    lambda sn=sender_name, ts=timestamp, bt=body_text, og=is_outgoing, ed=is_edited, mid=msg_id, mp=media_path:
                    self.display_chat_message(sn, ts, bt, outgoing=og, edited=ed, message_id=mid, media_path=mp)
                )

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
        self.append_message_to_area(message)

    def display_chat_message(self, sender_name, timestamp, message_text, outgoing=False, edited=False, message_id=None, media_path=None):
        self.append_chat_message_to_area(sender_name, timestamp, message_text, outgoing=outgoing, edited=edited, message_id=message_id, media_path=media_path)

    def send_message(self):
        if not self.client or not self.current_chat:
            self.show_warning("Выберите чат!")
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        self.message_entry.delete(0, tk.END)
        self.set_status("Отправка сообщения...", "busy")

        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send_message_async(message), self.loop)

    async def send_message_async(self, message):
        try:
            sent_msg = await self.client.send_message(self.current_chat, message)
            self.last_message_id = getattr(sent_msg, 'id', None)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda mid=self.last_message_id: self.display_chat_message("Я", timestamp, message, outgoing=True, message_id=mid, media_path=None))
            self.set_status("Подключен", "online")
        except Exception as e:
            logging.exception("Ошибка отправки")
            self.set_status(f"Ошибка отправки: {e}", "error")
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
            self.set_status(f"Отправка файла: {filename}", "busy")

            self.root.after(0, lambda: self.display_message(f"📤 Отправка: {filename} ({file_size // 1024} KB)"))

            def progress_callback(current, total):
                percent = int((current / total) * 100)
                bar_length = 20
                filled = int(bar_length * current / total)
                bar = '█' * filled + '░' * (bar_length - filled)
                progress_msg = f"⏳ {bar} {percent}%"
                self.root.after(0, lambda: self.update_last_message(progress_msg))

            await self.client.send_file(
                self.current_chat,
                filepath,
                progress_callback=progress_callback
            )

            self.root.after(0, lambda: self.remove_last_message())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.root.after(0, lambda: self.display_message(f"[{timestamp}] Я: ✅ Отправлен файл: {filename}"))
            self.set_status("Подключен", "online")

        except Exception as e:
            logging.exception("Ошибка отправки файла")
            self.root.after(0, lambda: self.remove_last_message())
            self.root.after(0, lambda: self.display_message(f"❌ Ошибка отправки: {filename}"))
            self.root.after(0, lambda: self.show_error(f"Ошибка отправки файла: {e}"))
            self.set_status("Ошибка отправки", "error")

    def update_last_message(self, new_text):
        """Обновляет последнюю строку в области сообщений"""
        # Получаем содержимое
        content = self.messages_area.get(1.0, tk.END)
        lines = content.split('\n')

        # Удаляем последние 2 строки (последняя пустая + строка прогресса)
        if len(lines) >= 2:
            lines = lines[:-2]

        # Добавляем обновленный прогресс
        lines.append(new_text)

        # Обновляем содержимое
        self.replace_messages_area_content(lines)

    def remove_last_message(self):
        """Удаляет последнюю строку из области сообщений"""
        content = self.messages_area.get(1.0, tk.END)
        lines = content.split('\n')

        if len(lines) >= 2:
            lines = lines[:-2]  # Удаляем последнюю строку и пустую

        self.replace_messages_area_content(lines)

    def edit_last_message(self):
        if not self.client or not self.current_chat:
            self.show_warning("Выберите чат!")
            return

        message_id = self.selected_message_id or self.last_message_id

        if not message_id:
            self.show_warning("Нет сообщений для редактирования!")
            return

        new_text = simpledialog.askstring(
            "Редактировать сообщение",
            "Введите новый текст:",
            parent=self.root
        )

        if new_text and new_text.strip() and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.edit_message_async(message_id, new_text.strip()),
                self.loop
            )

    async def edit_message_async(self, message_id, new_text):
        try:
            await self.client.edit_message(self.current_chat, message_id, new_text)
            self.root.after(0, lambda: asyncio.run_coroutine_threadsafe(
                self.load_messages(), self.loop
            ))
            self.root.after(0, lambda: self.show_info("Сообщение отредактировано!"))
        except MessageEditTimeExpiredError:
            error_text = "Редактирование недоступно: Telegram больше не позволяет изменить это старое сообщение."
            logging.warning(error_text)
            self.set_status("Сообщение слишком старое для редактирования", "warning")
            self.root.after(0, lambda msg=error_text: self.show_warning(msg))
        except Exception as e:
            logging.exception("Ошибка редактирования")
            error_text = f"Ошибка редактирования: {e}"
            self.set_status(error_text, "error")
            self.root.after(0, lambda msg=error_text: self.show_error(msg))

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
        if self.loop and self.client:
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
        self.is_closing = True
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
