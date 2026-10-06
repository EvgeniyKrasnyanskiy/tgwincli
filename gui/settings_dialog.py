import threading
import tkinter as tk
from tkinter import messagebox, ttk

from config.settings import (
    detect_tgws_proxy,
    get_proxy_settings,
    save_proxy_settings,
    test_proxy_connection,
)
from utils.app_icon import set_window_icon


class ProxySettingsDialog:
    MODE_OPTIONS = [
        ("auto", "Авто (Прямое -> MTProto)"),
        ("mtproto", "MTProto (TG WS Proxy)"),
        ("socks5", "SOCKS5"),
        ("direct", "Прямое (без прокси)"),
    ]

    def __init__(self, parent, on_save_callback=None):
        self.parent = parent
        self.on_save_callback = on_save_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки прокси")
        self.dialog.resizable(False, False)
        set_window_icon(self.dialog)

        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()
        self._load_current_settings()
        self._center_window()

    def _center_window(self):
        self.dialog.update_idletasks()
        width = 460
        height = 430
        p_x = self.parent.winfo_rootx()
        p_y = self.parent.winfo_rooty()
        p_w = self.parent.winfo_width()
        p_h = self.parent.winfo_height()

        x = p_x + max(0, (p_w - width) // 2)
        y = p_y + max(0, (p_h - height) // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        container = tk.Frame(self.dialog, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        # Mode
        mode_frame = tk.Frame(container)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(mode_frame, text="Режим работы:", font=("Arial", 10, "bold"), width=16, anchor="w").pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value="auto")
        self.mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=[label for _, label in self.MODE_OPTIONS],
            state="readonly",
            width=28,
        )
        self.mode_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())

        # Quick detect button
        tgws_btn = tk.Button(
            container,
            text="🔍 Автоопределение из TG WS Proxy",
            command=self._detect_tgws,
            bg="#e8f4fc",
            fg="#006699",
            font=("Arial", 9, "bold"),
            relief=tk.GROOVE,
            cursor="hand2",
            padx=8,
            pady=4,
        )
        tgws_btn.pack(fill=tk.X, pady=(0, 12))

        # Fields frame
        fields_frame = tk.LabelFrame(container, text="Параметры подключения", padx=10, pady=10)
        fields_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Host
        f_row1 = tk.Frame(fields_frame)
        f_row1.pack(fill=tk.X, pady=3)
        tk.Label(f_row1, text="Хост:", width=14, anchor="w").pack(side=tk.LEFT)
        self.host_entry = tk.Entry(f_row1)
        self.host_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Port
        f_row2 = tk.Frame(fields_frame)
        f_row2.pack(fill=tk.X, pady=3)
        tk.Label(f_row2, text="Порт:", width=14, anchor="w").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(f_row2)
        self.port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Secret (MTProto)
        self.secret_frame = tk.Frame(fields_frame)
        self.secret_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.secret_frame, text="Секрет (MTProto):", width=14, anchor="w").pack(side=tk.LEFT)
        self.secret_entry = tk.Entry(self.secret_frame)
        self.secret_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # SOCKS5 user/pass
        self.auth_frame = tk.Frame(fields_frame)
        self.auth_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.auth_frame, text="Логин SOCKS5:", width=14, anchor="w").pack(side=tk.LEFT)
        self.user_entry = tk.Entry(self.auth_frame)
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.pass_frame = tk.Frame(fields_frame)
        self.pass_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.pass_frame, text="Пароль SOCKS5:", width=14, anchor="w").pack(side=tk.LEFT)
        self.pass_entry = tk.Entry(self.pass_frame, show="*")
        self.pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Timeout
        f_row5 = tk.Frame(fields_frame)
        f_row5.pack(fill=tk.X, pady=3)
        tk.Label(f_row5, text="Таймаут (сек):", width=14, anchor="w").pack(side=tk.LEFT)
        self.timeout_entry = tk.Entry(f_row5)
        self.timeout_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Status / test message
        self.status_label = tk.Label(container, text="", font=("Arial", 9), anchor="w")
        self.status_label.pack(fill=tk.X, pady=(0, 8))

        # Action buttons
        btn_frame = tk.Frame(container)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        test_btn = tk.Button(
            btn_frame,
            text="⚡ Проверить",
            command=self._test_connection,
            font=("Arial", 9),
            padx=10,
            pady=4,
        )
        test_btn.pack(side=tk.LEFT)

        cancel_btn = tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            font=("Arial", 9),
            padx=12,
            pady=4,
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        save_btn = tk.Button(
            btn_frame,
            text="Сохранить и применить",
            command=self._save_settings,
            bg="#0088cc",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        save_btn.pack(side=tk.RIGHT)

    def _mode_key_from_label(self, label):
        for key, name in self.MODE_OPTIONS:
            if name == label or key == label:
                return key
        return "auto"

    def _mode_label_from_key(self, key):
        for k, name in self.MODE_OPTIONS:
            if k == key:
                return name
        return self.MODE_OPTIONS[0][1]

    def _on_mode_change(self):
        mode = self._mode_key_from_label(self.mode_var.get())
        is_direct = mode == "direct"
        is_socks = mode == "socks5"
        is_mtproto_or_auto = mode in ("mtproto", "auto")

        state = "disabled" if is_direct else "normal"
        self.host_entry.config(state=state)
        self.port_entry.config(state=state)

        if is_mtproto_or_auto:
            self.secret_entry.config(state="normal")
            self.user_entry.config(state="disabled")
            self.pass_entry.config(state="disabled")
        elif is_socks:
            self.secret_entry.config(state="disabled")
            self.user_entry.config(state="normal")
            self.pass_entry.config(state="normal")
        else:
            self.secret_entry.config(state="disabled")
            self.user_entry.config(state="disabled")
            self.pass_entry.config(state="disabled")

    def _load_current_settings(self):
        cfg = get_proxy_settings()
        self.mode_var.set(self._mode_label_from_key(cfg.get("mode", "auto")))
        self.host_entry.delete(0, tk.END)
        self.host_entry.insert(0, str(cfg.get("host", "127.0.0.1")))

        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(cfg.get("port", 1443)))

        self.secret_entry.delete(0, tk.END)
        self.secret_entry.insert(0, str(cfg.get("secret", "")))

        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, str(cfg.get("username", "")))

        self.pass_entry.delete(0, tk.END)
        self.pass_entry.insert(0, str(cfg.get("password", "")))

        self.timeout_entry.delete(0, tk.END)
        self.timeout_entry.insert(0, str(cfg.get("timeout", 12)))

        self._on_mode_change()

    def _detect_tgws(self):
        detected = detect_tgws_proxy()
        if not detected:
            self.status_label.config(
                text="TG WS Proxy не обнаружен в %APPDATA%\\TgWsProxy",
                fg="#c0392b",
            )
            return

        self.mode_var.set(self._mode_label_from_key("mtproto"))
        self.host_entry.delete(0, tk.END)
        self.host_entry.insert(0, detected.get("host", "127.0.0.1"))

        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(detected.get("port", 1443)))

        self.secret_entry.delete(0, tk.END)
        self.secret_entry.insert(0, detected.get("secret", ""))

        self._on_mode_change()
        self.status_label.config(
            text=f"Параметры загружены из TG WS Proxy (порт {detected.get('port')})",
            fg="#27ae60",
        )

    def _test_connection(self):
        host = self.host_entry.get().strip() or "127.0.0.1"
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            self.status_label.config(text="Укажите корректный числовой порт", fg="#c0392b")
            return

        self.status_label.config(text="Проверка соединения...", fg="#7f8c8d")

        def check_in_background():
            ok, msg = test_proxy_connection(host, port)
            def update_ui():
                if ok:
                    self.status_label.config(
                        text=f"Порт {port} на {host} доступен!",
                        fg="#27ae60",
                    )
                else:
                    self.status_label.config(
                        text=f"Ошибка соединения: {msg}",
                        fg="#c0392b",
                    )
            self.dialog.after(0, update_ui)

        threading.Thread(target=check_in_background, daemon=True).start()

    def _save_settings(self):
        mode = self._mode_key_from_label(self.mode_var.get())
        host = self.host_entry.get().strip()
        port_raw = self.port_entry.get().strip()
        secret = self.secret_entry.get().strip()
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        timeout_raw = self.timeout_entry.get().strip()

        if mode != "direct":
            if not host:
                messagebox.showerror("Ошибка", "Хост не может быть пустым!", parent=self.dialog)
                return
            try:
                port = int(port_raw)
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Порт должен быть числом от 1 до 65535!", parent=self.dialog)
                return
        else:
            port = 1443

        if mode == "mtproto" and not secret:
            messagebox.showerror("Ошибка", "Для MTProto режима обязательно укажите секретный ключ!", parent=self.dialog)
            return

        try:
            timeout = int(timeout_raw)
            if timeout <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Таймаут должен быть положительным числом секунд!", parent=self.dialog)
            return

        new_settings = {
            "mode": mode,
            "host": host,
            "port": port,
            "secret": secret,
            "username": username,
            "password": password,
            "timeout": timeout,
        }

        try:
            save_proxy_settings(new_settings)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}", parent=self.dialog)
            return

        self.dialog.destroy()

        if self.on_save_callback:
            self.on_save_callback(new_settings)
