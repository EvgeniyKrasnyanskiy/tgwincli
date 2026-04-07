import tkinter as tk
from tkinter import scrolledtext, ttk

def bind_entry_context_menu(entry):
    context_menu = tk.Menu(entry, tearoff=0)
    context_menu.add_command(
        label="Вырезать",
        command=lambda: entry.event_generate("<<Cut>>"),
    )
    context_menu.add_command(
        label="Копировать",
        command=lambda: entry.event_generate("<<Copy>>"),
    )
    context_menu.add_command(
        label="Вставить",
        command=lambda: entry.event_generate("<<Paste>>"),
    )
    context_menu.add_command(
        label="Удалить",
        command=lambda: entry.delete("sel.first", "sel.last") if entry.selection_present() else None,
    )
    context_menu.add_separator()
    context_menu.add_command(
        label="Выделить всё",
        command=lambda: (entry.focus_set(), entry.select_range(0, tk.END), entry.icursor(tk.END)),
    )

    def show_context_menu(event):
        entry.focus_set()
        context_menu.tk_popup(event.x_root, event.y_root)

    def select_all(event=None):
        entry.focus_set()
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)
        return "break"

    def cut_text(event=None):
        entry.focus_set()
        entry.event_generate("<<Cut>>")
        return "break"

    def copy_text(event=None):
        entry.focus_set()
        entry.event_generate("<<Copy>>")
        return "break"

    def paste_text(event=None):
        entry.focus_set()
        entry.event_generate("<<Paste>>")
        return "break"

    entry.bind("<Button-3>", show_context_menu)
    entry.bind("<Control-a>", select_all)
    entry.bind("<Control-A>", select_all)
    entry.bind("<Control-x>", cut_text)
    entry.bind("<Control-X>", cut_text)
    entry.bind("<Control-c>", copy_text)
    entry.bind("<Control-C>", copy_text)
    entry.bind("<Control-v>", paste_text)
    entry.bind("<Control-V>", paste_text)


def create_chat_list(parent):
    frame = tk.Frame(parent, width=200)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

    tk.Label(
        frame,
        text="Список контактов:",
        font=("Arial", 12, "bold"),
    )

    listbox = tk.Listbox(
        frame,
        width=25,
        font=("Arial", 11, "bold"),
        activestyle="none",
        selectbackground="#d9ecff",
        selectforeground="#12314d",
        highlightthickness=1,
        highlightbackground="#c4d7e6",
        relief=tk.FLAT,
        bd=0,
        exportselection=False,
    )
    listbox.pack(fill=tk.BOTH, expand=True)

    return listbox


def create_message_area(parent):
    frame = tk.Frame(parent)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    header_label = tk.Label(
        frame,
        text="История сообщений:",
        font=("Arial", 12, "bold"),
        anchor="center",
        justify=tk.CENTER,
    )
    header_label.pack(fill=tk.X)

    messages_area = scrolledtext.ScrolledText(
        frame,
        wrap=tk.WORD,
        state="normal",
        height=20,
        font=("Arial", 11),
        exportselection=False,
        cursor="xterm",
        insertwidth=0,
        selectbackground="#cfe5ff",
        selectforeground="#102030",
        inactiveselectbackground="#cfe5ff",
    )
    messages_area.pack(fill=tk.BOTH, expand=True, pady=5)

    return frame, header_label, messages_area


def create_input_panel(parent, callbacks):
    bottom_frame = tk.Frame(parent)
    bottom_frame.pack(fill=tk.X, pady=5)

    message_entry = tk.Entry(bottom_frame, font=("Arial", 11))
    message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    message_entry.bind("<Return>", lambda e: callbacks["send"]())
    bind_entry_context_menu(message_entry)

    tk.Button(
        bottom_frame,
        text="Отправить",
        command=callbacks["send"],
        bg="#0088cc",
        fg="white",
        font=("Arial", 11, "bold"),
        width=11,
        padx=8,
        pady=4,
    ).pack(side=tk.LEFT, padx=2)
    
    tk.Button(
        bottom_frame,
        text="Файл",
        command=callbacks["attach"],
        bg="#00aa00",
        fg="white",
        font=("Arial", 10),
    ).pack(side=tk.LEFT, padx=2)
    
    tk.Button(
        bottom_frame,
        text="Ред.",
        command=callbacks["edit"],
        bg="#ff9800",
        fg="white",
        font=("Arial", 10),
        width=6,
    ).pack(side=tk.LEFT, padx=2)

    return message_entry


def create_progress_label(parent):
    progress_frame = tk.Frame(parent)
    progress_frame.pack(fill=tk.X, pady=2)

    progress_label = tk.Label(progress_frame, text="", font=("Arial", 10), fg="blue")
    progress_label.pack(side=tk.LEFT)

    progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=200)
    progress_bar.pack(side=tk.LEFT, padx=5)

    return progress_frame, progress_label, progress_bar


def create_status_bar(parent):
    frame = tk.Frame(parent, bg="#eef3f7", bd=1, relief=tk.SOLID)
    frame.pack(fill=tk.X, side=tk.BOTTOM)

    status_dot = tk.Label(frame, text="●", bg="#eef3f7", fg="#6c7a86", font=("Arial", 10, "bold"))
    status_dot.pack(side=tk.LEFT, padx=(10, 6), pady=4)

    status_label = tk.Label(
        frame,
        text="Не подключено",
        bg="#eef3f7",
        fg="#2f3b45",
        anchor="w",
        font=("Arial", 9),
    )
    status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

    return frame, status_dot, status_label