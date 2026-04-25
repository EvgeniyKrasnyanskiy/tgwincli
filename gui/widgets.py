import tkinter as tk
from tkinter import scrolledtext, ttk


def bind_text_input_context_menu(text_input):
    context_menu = tk.Menu(text_input, tearoff=0)
    context_menu.add_command(
        label="Вырезать",
        command=lambda: text_input.event_generate("<<Cut>>"),
    )
    context_menu.add_command(
        label="Копировать",
        command=lambda: text_input.event_generate("<<Copy>>"),
    )
    context_menu.add_command(
        label="Вставить",
        command=lambda: text_input.event_generate("<<Paste>>"),
    )
    context_menu.add_command(
        label="Удалить",
        command=lambda: text_input.delete("sel.first", "sel.last") if text_input.tag_ranges(tk.SEL) else None,
    )
    context_menu.add_separator()
    context_menu.add_command(
        label="Выделить всё",
        command=lambda: select_all(),
    )

    def show_context_menu(event):
        text_input.focus_set()
        context_menu.tk_popup(event.x_root, event.y_root)

    def select_all(event=None):
        text_input.focus_set()
        text_input.tag_add(tk.SEL, "1.0", "end-1c")
        text_input.mark_set(tk.INSERT, "end-1c")
        text_input.see(tk.INSERT)
        return "break"

    def cut_text(event=None):
        text_input.focus_set()
        text_input.event_generate("<<Cut>>")
        return "break"

    def copy_text(event=None):
        text_input.focus_set()
        text_input.event_generate("<<Copy>>")
        return "break"

    def paste_text(event=None):
        text_input.focus_set()
        text_input.event_generate("<<Paste>>")
        return "break"

    text_input.bind("<Button-3>", show_context_menu)
    text_input.bind("<Control-a>", select_all)
    text_input.bind("<Control-A>", select_all)
    text_input.bind("<Control-x>", cut_text)
    text_input.bind("<Control-X>", cut_text)
    text_input.bind("<Control-c>", copy_text)
    text_input.bind("<Control-C>", copy_text)
    text_input.bind("<Control-v>", paste_text)
    text_input.bind("<Control-V>", paste_text)


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
    bottom_frame.grid_columnconfigure(0, weight=1)

    input_frame = tk.Frame(
        bottom_frame,
        highlightthickness=1,
        highlightbackground="#c4d7e6",
        bd=0,
    )
    input_frame.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    input_frame.grid_columnconfigure(0, weight=1)

    message_entry = tk.Text(
        input_frame,
        height=1,
        maxundo=50,
        wrap=tk.WORD,
        font=("Arial", 11),
        relief=tk.FLAT,
        padx=8,
        pady=6,
        borderwidth=0,
        highlightthickness=0,
        undo=True,
    )
    message_entry.grid(row=0, column=0, sticky="ew")
    message_entry.tag_configure("placeholder", foreground="#7f8c98")
    message_entry.placeholder_text = "Введите ваше сообщение"
    message_entry.placeholder_visible = False

    def update_input_height(event=None):
        message_entry.update_idletasks()
        try:
            display_lines = int(message_entry.count("1.0", "end-1c", "displaylines")[0])
        except (tk.TclError, TypeError):
            display_lines = int(message_entry.index("end-1c").split(".")[0])
        message_entry.configure(height=max(1, min(display_lines, 5)))

    def show_placeholder():
        if message_entry.get("1.0", "end-1c"):
            return
        message_entry.placeholder_visible = True
        message_entry.insert("1.0", message_entry.placeholder_text, ("placeholder",))
        message_entry.mark_set(tk.INSERT, "1.0")
        message_entry.see(tk.INSERT)
        message_entry.configure(height=1)

    def hide_placeholder():
        if not message_entry.placeholder_visible:
            return
        message_entry.placeholder_visible = False
        message_entry.delete("1.0", tk.END)

    def on_focus_in(event=None):
        if message_entry.placeholder_visible:
            message_entry.after_idle(lambda: message_entry.mark_set(tk.INSERT, "1.0"))
        return None

    def on_focus_out(event=None):
        if not message_entry.get("1.0", "end-1c").strip():
            message_entry.delete("1.0", tk.END)
            show_placeholder()

    def on_key_press(event=None):
        if message_entry.placeholder_visible and event.keysym not in {"Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"}:
            hide_placeholder()

    def send_from_input(event=None):
        if message_entry.placeholder_visible:
            return "break"
        hide_placeholder()
        callbacks["send"]()
        update_input_height()
        if not message_entry.get("1.0", "end-1c").strip():
            show_placeholder()
        return "break"

    def insert_newline(event=None):
        hide_placeholder()
        message_entry.insert(tk.INSERT, "\n")
        message_entry.after_idle(update_input_height)
        return "break"

    message_entry.bind("<FocusIn>", on_focus_in)
    message_entry.bind("<FocusOut>", on_focus_out)
    message_entry.bind("<KeyPress>", on_key_press, add="+")
    message_entry.bind("<Return>", send_from_input)
    message_entry.bind("<Shift-Return>", insert_newline)
    message_entry.bind("<KeyRelease>", update_input_height, add="+")
    message_entry.bind("<<Paste>>", lambda event: (hide_placeholder(), message_entry.after_idle(update_input_height)), add="+")
    bind_text_input_context_menu(message_entry)
    show_placeholder()

    button_frame = tk.Frame(bottom_frame)
    button_frame.grid(row=0, column=1, sticky="e")

    button_options = {
        "font": ("Arial", 10, "bold"),
        "width": 10,
        "height": 2,
        "padx": 6,
        "pady": 4,
    }

    tk.Button(
        button_frame,
        text="Отправить",
        command=callbacks["send"],
        bg="#0088cc",
        fg="white",
        **button_options,
    ).grid(row=0, column=0, sticky="ew", padx=2)

    tk.Button(
        button_frame,
        text="Файл",
        command=callbacks["attach"],
        bg="#00aa00",
        fg="white",
        **button_options,
    ).grid(row=0, column=1, sticky="ew", padx=2)

    tk.Button(
        button_frame,
        text="Ред.",
        command=callbacks["edit"],
        bg="#ff9800",
        fg="white",
        **button_options,
    ).grid(row=0, column=2, sticky="ew", padx=2)

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
