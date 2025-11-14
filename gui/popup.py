import tkinter as tk
import asyncio
from config.settings import POPUP_BASE_WIDTH, POPUP_BASE_HEIGHT


# def create_popup(root, sender_name, message, chat_id, callbacks):
#     """Создаёт popup окно с уведомлением"""
#     popup = tk.Toplevel(root)
#     popup.overrideredirect(True)
#
#     base_width = POPUP_BASE_WIDTH
#     base_height = POPUP_BASE_HEIGHT
#     message_length = len(message)
#
#     if message_length > 100:
#         extra_height = min((message_length - 100) // 2, 200)
#         base_height += extra_height
#     if message_length > 200:
#         base_width = 450
#
#     popup.attributes('-topmost', True)
#
#     screen_width = popup.winfo_screenwidth()
#     screen_height = popup.winfo_screenheight()
#     x = (screen_width / 2) - (base_width / 2)
#     y = (screen_height / 2) - (base_height / 2)
#     popup.geometry(f"{base_width}x{base_height}+{int(x)}+{int(y)}")
#
#     popup.configure(bg='#f0f0f0', highlightthickness=3, highlightbackground='#0088cc')
#
#     content_frame = tk.Frame(popup, bg='#f0f0f0')
#     content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
#
#     tk.Label(content_frame, text=f"от: {sender_name}",
#              bg='#f0f0f0', font=("Arial", 11)).pack(anchor='w', pady=(0, 10))
#
#     message_frame = tk.Frame(content_frame, bg='#f0f0f0')
#     message_frame.pack(fill=tk.BOTH, expand=True, pady=5)
#
#     if message_length > 150:
#         scrollbar = tk.Scrollbar(message_frame)
#         scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
#
#         message_text = tk.Text(message_frame, wrap=tk.WORD, bg='#f0f0f0',
#                                font=("Arial", 14, "bold italic"), relief=tk.FLAT,
#                                yscrollcommand=scrollbar.set, height=8)
#         message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
#         message_text.insert(1.0, f"✉ {message}")
#         message_text.config(state='disabled')
#         scrollbar.config(command=message_text.yview)
#     else:
#         message_label = tk.Label(message_frame, text=f"✉ {message}",
#                                  wraplength=base_width - 60, bg='#f0f0f0',
#                                  font=("Arial", 14, "bold italic"), justify=tk.LEFT)
#         message_label.pack(fill=tk.BOTH, expand=True)
#
#     button_frame = tk.Frame(content_frame, bg='#f0f0f0')
#     button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))
#
#     def reply():
#         popup.destroy()
#         callbacks['on_reply'](popup, chat_id)
#
#     def close():
#         popup.destroy()
#         callbacks['on_close'](popup, message, chat_id)
#
#     tk.Button(button_frame, text="Ответить", command=reply,
#               bg="#0088cc", fg="white", font=("Arial", 11, "bold"),
#               padx=20, pady=8, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=8)
#     tk.Button(button_frame, text="Закрыть", command=close,
#               bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
#               padx=20, pady=8, relief=tk.FLAT, cursor="hand2").pack(side=tk.LEFT, padx=8)
#
#     return popup

def create_popup(root, sender_name, message, chat_id, callbacks):
    """Создаёт popup окно с уведомлением (кнопки слева/справа, текст с прокруткой)"""
    popup = tk.Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes('-topmost', True)

    base_width = POPUP_BASE_WIDTH
    base_height = POPUP_BASE_HEIGHT
    message_length = len(message)

    if message_length > 200:
        base_width = 460
    elif message_length > 100:
        base_width = 430

    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()
    x = (screen_width / 2) - (base_width / 2)
    y = (screen_height / 2) - (base_height / 2)
    popup.geometry(f"{base_width}x{base_height}+{int(x)}+{int(y)}")

    popup.configure(bg='#f0f0f0', highlightthickness=3, highlightbackground='#0088cc')

    content_frame = tk.Frame(popup, bg='#f0f0f0')
    content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    # Сетка: заголовок, сообщение, кнопки
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_rowconfigure(1, weight=1)

    header = tk.Label(content_frame, text=f"от: {sender_name}",
                      bg='#f0f0f0', font=("Arial", 11))
    header.grid(row=0, column=0, sticky="w", pady=(0, 8))

    # Сообщение с прокруткой
    message_container = tk.Frame(content_frame, bg='#f0f0f0')
    message_container.grid(row=1, column=0, sticky="nsew")

    message_container.grid_columnconfigure(0, weight=1)
    message_container.grid_rowconfigure(0, weight=1)

    scrollbar = tk.Scrollbar(message_container)
    scrollbar.grid(row=0, column=1, sticky="ns")

    message_text = tk.Text(message_container, wrap=tk.WORD, bg='#f0f0f0',
                           font=("Arial", 14, "bold italic"), relief=tk.FLAT,
                           yscrollcommand=scrollbar.set, height=7)
    message_text.grid(row=0, column=0, sticky="nsew")
    message_text.insert("1.0", f"✉ {message}")
    message_text.config(state='disabled')
    scrollbar.config(command=message_text.yview)

    # Кнопки: одна слева, другая справа
    button_frame = tk.Frame(content_frame, bg='#f0f0f0')
    button_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)

    def reply():
        popup.destroy()
        callbacks['on_reply'](popup, chat_id)

    def close():
        popup.destroy()
        callbacks['on_close'](popup, message, chat_id)

    btn_reply = tk.Button(button_frame, text="Ответить", command=reply,
                          bg="#0088cc", fg="white", font=("Arial", 11, "bold"),
                          padx=20, pady=8, relief=tk.FLAT, cursor="hand2")
    btn_reply.grid(row=0, column=0, sticky="w")

    btn_close = tk.Button(button_frame, text="Закрыть", command=close,
                          bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
                          padx=20, pady=8, relief=tk.FLAT, cursor="hand2")
    btn_close.grid(row=0, column=1, sticky="e")

    return popup

