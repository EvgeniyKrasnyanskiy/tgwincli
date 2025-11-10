import tkinter as tk
from tkinter import scrolledtext, ttk


def create_chat_list(parent):
    """Создаёт список чатов"""
    frame = tk.Frame(parent, width=200)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

    tk.Label(frame, text="Список контактов:", font=("Arial", 12, "bold")).pack()

    listbox = tk.Listbox(frame, width=25, font=("Arial", 11, "bold"))  # Увеличен шрифт и жирный
    listbox.pack(fill=tk.BOTH, expand=True)

    return listbox


def create_message_area(parent):
    """Создаёт область сообщений"""
    frame = tk.Frame(parent)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(frame, text="История сообщений:", font=("Arial", 12, "bold")).pack()

    messages_area = scrolledtext.ScrolledText(
        frame,
        wrap=tk.WORD,
        state='disabled',
        height=20,
        font=("Arial", 11)  # Увеличен шрифт
    )
    messages_area.pack(fill=tk.BOTH, expand=True, pady=5)

    return frame, messages_area


def create_input_panel(parent, callbacks):
    """Создаёт панель ввода"""
    bottom_frame = tk.Frame(parent)
    bottom_frame.pack(fill=tk.X, pady=5)

    message_entry = tk.Entry(bottom_frame, font=("Arial", 11))  # Увеличен шрифт
    message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    message_entry.bind('<Return>', lambda e: callbacks['send']())

    # Добавляем контекстное меню для вставки
    context_menu = tk.Menu(message_entry, tearoff=0)
    context_menu.add_command(
        label="Вставить (Ctrl+V)",
        command=lambda: message_entry.event_generate('<<Paste>>')
    )

    def show_context_menu(event):
        context_menu.post(event.x_root, event.y_root)

    message_entry.bind('<Button-3>', show_context_menu)  # Правая кнопка мыши

    # Биндинг Ctrl+V для вставки
    message_entry.bind('<Control-v>', lambda e: None)  # Стандартная вставка работает автоматически

    tk.Button(bottom_frame, text="Отправить", command=callbacks['send'],
              bg="#0088cc", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
    tk.Button(bottom_frame, text="📎 Файл", command=callbacks['attach'],
              bg="#00aa00", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
    tk.Button(bottom_frame, text="✏️ Редактировать", command=callbacks['edit'],
              bg="#ff9800", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

    return message_entry


def create_progress_label(parent):
    """Создаёт метку для отображения прогресса"""
    progress_frame = tk.Frame(parent)
    progress_frame.pack(fill=tk.X, pady=2)

    progress_label = tk.Label(progress_frame, text="", font=("Arial", 10), fg="blue")
    progress_label.pack(side=tk.LEFT)

    progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=200)
    progress_bar.pack(side=tk.LEFT, padx=5)

    return progress_frame, progress_label, progress_bar