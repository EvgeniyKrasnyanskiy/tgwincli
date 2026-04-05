import tkinter as tk

from config.settings import POPUP_BASE_HEIGHT, POPUP_BASE_WIDTH


def create_popup(root, sender_name, message, chat_id, callbacks):
    popup = tk.Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)

    base_width = POPUP_BASE_WIDTH
    base_height = POPUP_BASE_HEIGHT
    message_length = len(message)

    if message_length > 100:
        base_height += min((message_length - 100) // 3, 220)
    if message_length > 200:
        base_width = 460

    base_height = min(base_height, 520)

    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()
    x = (screen_width / 2) - (base_width / 2)
    y = (screen_height / 2) - (base_height / 2)
    popup.geometry(f"{base_width}x{base_height}+{int(x)}+{int(y)}")
    popup.minsize(360, 220)

    popup.configure(bg="#f0f0f0", highlightthickness=3, highlightbackground="#0088cc")

    content_frame = tk.Frame(popup, bg="#f0f0f0")
    content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_rowconfigure(1, weight=1)

    tk.Label(
        content_frame,
        text=f"\u041e\u0442: {sender_name}",
        bg="#f0f0f0",
        font=("Arial", 11),
    ).grid(row=0, column=0, sticky="w", pady=(0, 10))

    message_frame = tk.Frame(
        content_frame,
        bg="#ffffff",
        highlightthickness=1,
        highlightbackground="#c9d7e1",
        bd=0,
    )
    message_frame.grid(row=1, column=0, sticky="nsew", pady=5)
    message_frame.grid_columnconfigure(0, weight=1)
    message_frame.grid_rowconfigure(0, weight=1)

    scrollbar = tk.Scrollbar(message_frame, troughcolor="#eef3f7", bg="#d8e2ea", activebackground="#b8c8d6")
    scrollbar.grid(row=0, column=1, sticky="ns")

    visible_lines = max(5, min(12, (message.count("\n") + 1) + max(0, message_length // 90)))
    message_text = tk.Text(
        message_frame,
        wrap=tk.WORD,
        bg="#ffffff",
        font=("Arial", 14, "bold italic"),
        relief=tk.FLAT,
        yscrollcommand=scrollbar.set,
        height=visible_lines,
        padx=10,
        pady=10,
        borderwidth=0,
        highlightthickness=0,
    )
    message_text.grid(row=0, column=0, sticky="nsew")
    message_text.insert("1.0", f"\u2709 {message}")
    message_text.config(state="disabled")
    scrollbar.config(command=message_text.yview)

    button_frame = tk.Frame(content_frame, bg="#f0f0f0")
    button_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))

    def reply():
        popup.destroy()
        callbacks["on_reply"](popup, chat_id)

    def close():
        popup.destroy()
        callbacks["on_close"](popup, message, chat_id)

    tk.Button(
        button_frame,
        text="\u041e\u0442\u0432\u0435\u0442\u0438\u0442\u044c",
        command=reply,
        bg="#0088cc",
        fg="white",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
        cursor="hand2",
    ).pack(side=tk.LEFT, padx=8)
    tk.Button(
        button_frame,
        text="\u0417\u0430\u043a\u0440\u044b\u0442\u044c",
        command=close,
        bg="#dc3545",
        fg="white",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=8,
        relief=tk.FLAT,
        cursor="hand2",
    ).pack(side=tk.RIGHT, padx=8)

    return popup
