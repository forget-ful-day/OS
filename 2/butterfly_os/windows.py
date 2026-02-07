import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import (
    APPS_DIR,
    FEATURE_TOGGLES,
    FS_DIR,
    STORE_DIR,
    THEMES,
    THEME_LABELS,
    USERS_PATH,
    save_json,
)
from .ui_components import RoundedButton


class BootScreen(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=theme["desktop_bg"])
        self.label = tk.Label(
            self,
            text="Butterfly OS 13",
            font=("Segoe UI", 24, "bold"),
            bg=theme["desktop_bg"],
            fg=theme["accent"],
        )
        self.label.pack(expand=True, fill="both", padx=40, pady=40)
        self.update_idletasks()
        width = 420
        height = 220
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=40, pady=(0, 30))
        self.progress.start(10)


class Window(tk.Toplevel):
    def __init__(self, master, title, theme, on_close=None):
        super().__init__(master)
        self.master = master
        self.theme = theme
        self.on_close = on_close
        self.configure(bg=theme["window_bg"])
        self.title(title)
        self.attributes("-fullscreen", True)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._make_title_bar(title)

    def _make_title_bar(self, title):
        bar = tk.Frame(self, bg=self.theme["taskbar_bg"], height=30)
        bar.pack(fill="x", side="top")
        tk.Label(
            bar,
            text=title,
            bg=self.theme["taskbar_bg"],
            fg=self.theme["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=8)
        btn_frame = tk.Frame(bar, bg=self.theme["taskbar_bg"])
        btn_frame.pack(side="right")
        tk.Button(
            btn_frame,
            text="—",
            width=3,
            command=self.iconify,
            bg=self.theme["taskbar_bg"],
            fg=self.theme["text"],
            relief="flat",
        ).pack(side="left")
        tk.Button(
            btn_frame,
            text="✕",
            width=3,
            command=self.close,
            bg=self.theme["taskbar_bg"],
            fg=self.theme["text"],
            relief="flat",
        ).pack(side="left")
        self.bind("<Escape>", lambda event: self.close())

    def close(self):
        if self.on_close:
            self.on_close()
        self.destroy()


class FileExplorer(Window):
    def __init__(self, master, theme, path):
        super().__init__(master, "Проводник", theme)
        self.path = path
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(body)
        self.listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(body, command=self.listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Double-Button-1>", self.open_item)
        buttons = tk.Frame(body, bg=theme["window_bg"])
        buttons.pack(side="right", fill="y", padx=10, pady=10)
        RoundedButton(buttons, "Импорт файлов", self.upload_file, theme, width=160).pack(pady=4)
        RoundedButton(buttons, "Новая папка", self.create_folder, theme, width=140).pack(pady=4)
        RoundedButton(buttons, "Открыть", self.open_item, theme, width=140).pack(pady=4)
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for entry in sorted(os.listdir(self.path)):
            self.listbox.insert(tk.END, entry)

    def open_item(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        name = self.listbox.get(selection[0])
        full_path = os.path.join(self.path, name)
        if os.path.isdir(full_path):
            FileExplorer(self.master, self.theme, full_path)
            return
        if name.lower().endswith((".txt", ".md", ".py", ".json")):
            TextViewer(self.master, self.theme, full_path)
            return
        if name.lower().endswith((".png", ".gif", ".ppm", ".pgm")):
            ImageViewer(self.master, self.theme, full_path)
            return
        messagebox.showinfo("Butterfly OS", f"Файл: {name}\nПуть: {full_path}")

    def upload_file(self):
        file_paths = filedialog.askopenfilenames()
        if not file_paths:
            return
        for file_path in file_paths:
            shutil.copy(file_path, self.path)
        self.refresh()

    def create_folder(self):
        folder_name = tk.simpledialog.askstring("Новая папка", "Имя папки:")
        if not folder_name:
            return
        os.makedirs(os.path.join(self.path, folder_name), exist_ok=True)
        self.refresh()


class TextViewer(Window):
    def __init__(self, master, theme, file_path):
        super().__init__(master, f"Текст - {os.path.basename(file_path)}", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        text = tk.Text(body, wrap="word")
        text.pack(fill="both", expand=True)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            text.insert("1.0", file.read())


class ImageViewer(Window):
    def __init__(self, master, theme, file_path):
        super().__init__(master, f"Фото - {os.path.basename(file_path)}", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        try:
            self.photo = tk.PhotoImage(file=file_path)
            label = tk.Label(body, image=self.photo, bg=theme["window_bg"])
            label.pack(expand=True)
        except tk.TclError:
            tk.Label(
                body,
                text="Формат изображения не поддерживается Tk.",
                bg=theme["window_bg"],
                fg=theme["text"],
            ).pack(expand=True)


class AppInstaller(Window):
    def __init__(self, master, theme, on_install):
        super().__init__(master, "Магазин приложений", theme)
        self.on_install = on_install
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(body)
        self.listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        for entry in sorted(os.listdir(STORE_DIR)):
            if entry.endswith(".butterfly"):
                self.listbox.insert(tk.END, entry)
        RoundedButton(body, "Установить", self.install_selected, theme, width=120).pack(side="right", padx=10)
        RoundedButton(body, "Установить из файла", self.install_from_file, theme, width=180).pack(
            side="right", padx=10
        )

    def install_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        name = self.listbox.get(selection[0])
        src = os.path.join(STORE_DIR, name)
        dst = os.path.join(APPS_DIR, name)
        if os.path.exists(dst):
            messagebox.showinfo("Butterfly OS", "Уже установлено.")
            return
        shutil.copytree(src, dst)
        self.on_install()
        messagebox.showinfo("Butterfly OS", f"Установлено: {name}.")

    def install_from_file(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        if not folder.endswith(".butterfly"):
            messagebox.showerror("Butterfly OS", "Нужна папка с расширением .butterfly.")
            return
        name = os.path.basename(folder)
        dst = os.path.join(APPS_DIR, name)
        if os.path.exists(dst):
            messagebox.showinfo("Butterfly OS", "Уже установлено.")
            return
        shutil.copytree(folder, dst)
        self.on_install()
        messagebox.showinfo("Butterfly OS", f"Установлено: {name}.")


class SettingsWindow(Window):
    def __init__(self, master, theme, config, users, on_update):
        super().__init__(master, "Настройки", theme)
        self.config = config
        self.users = users
        self.on_update = on_update
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(body, text="Тема", bg=theme["window_bg"], fg=theme["text"]).pack(anchor="w")
        self.theme_var = tk.StringVar(value=config.get("theme", "light"))
        for key in THEMES:
            tk.Radiobutton(
                body,
                text=THEME_LABELS.get(key, key.title()),
                variable=self.theme_var,
                value=key,
                bg=theme["window_bg"],
                fg=theme["text"],
                selectcolor=theme["window_bg"],
            ).pack(anchor="w")
        RoundedButton(body, "Применить тему", self.apply_theme, theme, width=160).pack(pady=6)
        tk.Label(body, text="Пользователи", bg=theme["window_bg"], fg=theme["text"]).pack(anchor="w", pady=(12, 0))
        self.user_list = tk.Listbox(body, height=4)
        self.user_list.pack(fill="x")
        for name in self.users["users"]:
            self.user_list.insert(tk.END, name)
        RoundedButton(body, "Добавить пользователя", self.add_user, theme, width=200).pack(pady=4)

    def apply_theme(self):
        self.config["theme"] = self.theme_var.get()
        self.on_update()

    def add_user(self):
        username = tk.simpledialog.askstring("Новый пользователь", "Имя пользователя:")
        if not username:
            return
        if username in self.users["users"]:
            messagebox.showerror("Butterfly OS", "Пользователь уже существует.")
            return
        password = tk.simpledialog.askstring("Новый пользователь", "Пароль:", show="*")
        if not password:
            return
        self.users["users"][username] = {"password": password}
        save_json(USERS_PATH, self.users)
        self.user_list.insert(tk.END, username)
        messagebox.showinfo("Butterfly OS", "Пользователь создан.")


class ControlCenter(Window):
    def __init__(self, master, theme, config, on_update):
        super().__init__(master, "Центр управления", theme)
        self.config = config
        self.on_update = on_update
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(
            body,
            text="Быстрые функции (25)",
            bg=theme["window_bg"],
            fg=theme["text"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(body, bg=theme["window_bg"])
        grid.pack(fill="both", expand=True)
        self.toggle_vars = {}
        for idx, name in enumerate(FEATURE_TOGGLES):
            var = tk.BooleanVar(value=self.config.get("toggles", {}).get(name, False))
            self.toggle_vars[name] = var
            row = idx // 3
            col = idx % 3
            card = tk.Frame(grid, bg=theme["taskbar_bg"], highlightbackground=theme["accent"], highlightthickness=1)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            tk.Label(card, text=name, bg=theme["taskbar_bg"], fg=theme["text"]).pack(padx=8, pady=(8, 4))
            toggle = ttk.Checkbutton(card, variable=var, command=self.persist_toggles)
            toggle.pack(pady=(0, 8))
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)

    def persist_toggles(self):
        self.config["toggles"] = {name: var.get() for name, var in self.toggle_vars.items()}
        self.on_update()


class GenericAppWindow(Window):
    def __init__(self, master, theme, title, description):
        super().__init__(master, title, theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            body,
            text=title,
            font=("Segoe UI", 16, "bold"),
            bg=theme["window_bg"],
            fg=theme["text"],
        ).pack(anchor="w")
        tk.Label(
            body,
            text=description,
            bg=theme["window_bg"],
            fg=theme["text"],
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=10)


class CalculatorWindow(Window):
    def __init__(self, master, theme):
        super().__init__(master, "Калькулятор", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=20, pady=20)
        self.display = tk.Entry(body, font=("Segoe UI", 16))
        self.display.pack(fill="x", pady=(0, 10))
        buttons = [
            "7",
            "8",
            "9",
            "/",
            "4",
            "5",
            "6",
            "*",
            "1",
            "2",
            "3",
            "-",
            "0",
            ".",
            "=",
            "+",
        ]
        grid = tk.Frame(body, bg=theme["window_bg"])
        grid.pack()
        for idx, label in enumerate(buttons):
            btn = RoundedButton(grid, label, lambda l=label: self.on_press(l), theme, width=60, height=40)
            btn.grid(row=idx // 4, column=idx % 4, padx=6, pady=6)
        RoundedButton(body, "Очистить", self.clear, theme, width=120).pack(pady=(12, 0))

    def on_press(self, label):
        if label == "=":
            try:
                result = eval(self.display.get(), {})
                self.display.delete(0, tk.END)
                self.display.insert(0, str(result))
            except Exception:
                self.display.delete(0, tk.END)
                self.display.insert(0, "Ошибка")
            return
        self.display.insert(tk.END, label)

    def clear(self):
        self.display.delete(0, tk.END)


class PaintWindow(Window):
    def __init__(self, master, theme):
        super().__init__(master, "Paint", theme)
        self.theme = theme
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        toolbar = tk.Frame(body, bg=theme["taskbar_bg"])
        toolbar.pack(fill="x")
        self.color = "#000000"
        colors = ["#000000", "#ff0000", "#00a300", "#0067c0", "#ffb900", "#ffffff"]
        for color in colors:
            RoundedButton(toolbar, " ", lambda c=color: self.set_color(c), theme, width=32, height=32).pack(
                side="left", padx=4, pady=4
            )
        RoundedButton(toolbar, "Сохранить", self.save_canvas, theme, width=120, height=32).pack(
            side="right", padx=6, pady=4
        )
        RoundedButton(toolbar, "Очистить", self.clear_canvas, theme, width=120, height=32).pack(
            side="right", padx=6, pady=4
        )
        self.canvas = tk.Canvas(body, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<B1-Motion>", self.draw)

    def set_color(self, color):
        self.color = color

    def draw(self, event):
        x, y = event.x, event.y
        self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=self.color, outline=self.color)

    def clear_canvas(self):
        self.canvas.delete("all")

    def save_canvas(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps")])
        if not file_path:
            return
        self.canvas.postscript(file=file_path)
        messagebox.showinfo("Butterfly OS", "Рисунок сохранён.")


class GalleryWindow(Window):
    def __init__(self, master, theme):
        super().__init__(master, "Галерея", theme)
        self.path = FS_DIR
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(body)
        self.listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(body, command=self.listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Double-Button-1>", self.open_image)
        RoundedButton(body, "Обновить", self.refresh, theme, width=120).pack(side="right", padx=10)
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for entry in sorted(os.listdir(self.path)):
            if entry.lower().endswith((".png", ".gif", ".ppm", ".pgm")):
                self.listbox.insert(tk.END, entry)

    def open_image(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        name = self.listbox.get(selection[0])
        full_path = os.path.join(self.path, name)
        ImageViewer(self.master, self.theme, full_path)


class MediaPlayerWindow(Window):
    def __init__(self, master, theme):
        super().__init__(master, "Медиаплеер", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            body,
            text="Откройте аудио или видео файл для воспроизведения внешним плеером.",
            bg=theme["window_bg"],
            fg=theme["text"],
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))
        RoundedButton(body, "Выбрать файл", self.open_external, theme, width=160).pack(pady=6)
        self.path_label = tk.Label(body, text="", bg=theme["window_bg"], fg=theme["text"])
        self.path_label.pack(anchor="w", pady=6)

    def open_external(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        self.path_label.config(text=f"Файл: {file_path}")
        opener = getattr(os, "startfile", None)
        if opener is None:
            messagebox.showinfo("Butterfly OS", "Открытие внешних файлов доступно только в Windows.")
            return
        try:
            opener(file_path)
        except OSError:
            messagebox.showinfo("Butterfly OS", "Не удалось открыть файл.")


class DocumentsWindow(Window):
    def __init__(self, master, theme):
        super().__init__(master, "Документы", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            body,
            text="Быстрый доступ к файловой системе Butterfly OS.",
            bg=theme["window_bg"],
            fg=theme["text"],
        ).pack(anchor="w", pady=(0, 10))
        RoundedButton(body, "Открыть проводник", lambda: FileExplorer(self.master, theme, FS_DIR), theme, width=200).pack(
            pady=6
        )


class LoginScreen(tk.Toplevel):
    def __init__(self, master, theme, users, on_login):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=theme["desktop_bg"])
        self.users = users
        self.on_login = on_login
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        frame = tk.Frame(self, bg=theme["desktop_bg"])
        frame.pack(expand=True)
        tk.Label(
            frame,
            text="Добро пожаловать в Butterfly OS",
            font=("Segoe UI", 20, "bold"),
            bg=theme["desktop_bg"],
            fg=theme["accent"],
        ).pack(pady=10)
        tk.Label(frame, text="Выберите пользователя", bg=theme["desktop_bg"], fg=theme["text"]).pack()
        self.user_var = tk.StringVar(value=list(users["users"].keys())[0])
        user_menu = ttk.Combobox(frame, textvariable=self.user_var, values=list(users["users"].keys()))
        user_menu.pack(pady=4)
        tk.Label(frame, text="Пароль", bg=theme["desktop_bg"], fg=theme["text"]).pack()
        self.pass_entry = tk.Entry(frame, show="*")
        self.pass_entry.pack(pady=4)
        RoundedButton(frame, "Войти", self.login, theme, width=140).pack(pady=8)

    def login(self):
        user = self.user_var.get()
        password = self.pass_entry.get()
        if self.users["users"].get(user, {}).get("password") == password:
            self.on_login(user)
            self.destroy()
        else:
            messagebox.showerror("Butterfly OS", "Неверный пароль.")
