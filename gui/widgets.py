import tkinter as tk
from tkinter import scrolledtext, ttk


def bind_entry_context_menu(entry):
    context_menu = tk.Menu(entry, tearoff=0)
    context_menu.add_command(
        label="\u0412\u044b\u0440\u0435\u0437\u0430\u0442\u044c (Ctrl+X)",
        command=lambda: entry.event_generate("<<Cut>>"),
    )
    context_menu.add_command(
        label="\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c (Ctrl+C)",
        command=lambda: entry.event_generate("<<Copy>>"),
    )
    context_menu.add_command(
        label="\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c (Ctrl+V)",
        command=lambda: entry.event_generate("<<Paste>>"),
    )
    context_menu.add_command(
        label="\u0423\u0434\u0430\u043b\u0438\u0442\u044c",
        command=lambda: entry.delete("sel.first", "sel.last") if entry.selection_present() else None,
    )
    context_menu.add_separator()
    context_menu.add_command(
        label="\u0412\u044b\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u0441\u0435 (Ctrl+A)",
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
        text="\u0421\u043f\u0438\u0441\u043e\u043a \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u043e\u0432:",
        font=("Arial", 12, "bold"),
    ).pack()

    listbox = tk.Listbox(frame, width=25, font=("Arial", 11, "bold"))
    listbox.pack(fill=tk.BOTH, expand=True)

    return listbox


def create_message_area(parent):
    frame = tk.Frame(parent)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(
        frame,
        text="\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0439:",
        font=("Arial", 12, "bold"),
    ).pack()

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

    return frame, messages_area


def create_input_panel(parent, callbacks):
    bottom_frame = tk.Frame(parent)
    bottom_frame.pack(fill=tk.X, pady=5)

    message_entry = tk.Entry(bottom_frame, font=("Arial", 11))
    message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    message_entry.bind("<Return>", lambda e: callbacks["send"]())
    bind_entry_context_menu(message_entry)

    tk.Button(
        bottom_frame,
        text="\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c",
        command=callbacks["send"],
        bg="#0088cc",
        fg="white",
        font=("Arial", 10),
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        bottom_frame,
        text="\U0001F4CE \u0424\u0430\u0439\u043b",
        command=callbacks["attach"],
        bg="#00aa00",
        fg="white",
        font=("Arial", 10),
    ).pack(side=tk.LEFT, padx=2)
    tk.Button(
        bottom_frame,
        text="\u270F\uFE0F \u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c",
        command=callbacks["edit"],
        bg="#ff9800",
        fg="white",
        font=("Arial", 10),
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

    status_dot = tk.Label(frame, text="\u25cf", bg="#eef3f7", fg="#6c7a86", font=("Arial", 10, "bold"))
    status_dot.pack(side=tk.LEFT, padx=(10, 6), pady=4)

    status_label = tk.Label(
        frame,
        text="\u041d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d",
        bg="#eef3f7",
        fg="#2f3b45",
        anchor="w",
        font=("Arial", 9),
    )
    status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

    return frame, status_dot, status_label
