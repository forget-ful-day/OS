import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FS_DIR = os.path.join(BASE_DIR, "butterfly_fs")
APPS_DIR = os.path.join(BASE_DIR, "apps_installed")
STORE_DIR = os.path.join(BASE_DIR, "store")
CONFIG_PATH = os.path.join(DATA_DIR, "settings.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")

DEFAULT_CONFIG = {
    "theme": "light",
    "icon_positions": {},
    "last_user": "admin",
}

DEFAULT_USERS = {
    "users": {
        "admin": {
            "password": "admin",
        }
    }
}

THEMES = {
    "light": {
        "desktop_bg": "#dde7f5",
        "taskbar_bg": "#f7f7fb",
        "window_bg": "#ffffff",
        "text": "#1f1f1f",
        "accent": "#2b59ff",
    },
    "dark": {
        "desktop_bg": "#1b1f2a",
        "taskbar_bg": "#10131a",
        "window_bg": "#1e2430",
        "text": "#e6e6e6",
        "accent": "#7aa2ff",
    },
    "neon": {
        "desktop_bg": "#0b0014",
        "taskbar_bg": "#120020",
        "window_bg": "#1a0030",
        "text": "#f7e8ff",
        "accent": "#ff4dff",
    },
}

THEME_LABELS = {
    "light": "Светлая",
    "dark": "Тёмная",
    "neon": "Butterfly Neon",
}

ICON_STYLES = {
    "Проводник": {"color": "#4e79ff", "symbol": "📁"},
    "Настройки": {"color": "#7a7a7a", "symbol": "⚙️"},
    "Магазин приложений": {"color": "#ff7b2f", "symbol": "🛒"},
    "Центр управления": {"color": "#20c997", "symbol": "🎛️"},
    "Игры": {"color": "#ff5c7a", "symbol": "🎮"},
    "Медиаплеер": {"color": "#6f42c1", "symbol": "🎵"},
    "Галерея": {"color": "#0dcaf0", "symbol": "🖼️"},
    "Календарь": {"color": "#ffc107", "symbol": "📅"},
    "Калькулятор": {"color": "#198754", "symbol": "🧮"},
    "Погода": {"color": "#0d6efd", "symbol": "☀️"},
    "Документы": {"color": "#fd7e14", "symbol": "📄"},
}

FEATURE_TOGGLES = [
    "Фокус-режим",
    "Ночной свет",
    "Wi‑Fi",
    "Bluetooth",
    "Режим полета",
    "Экономия батареи",
    "Уведомления",
    "Быстрая отправка",
    "Облачная синхронизация",
    "Автообновления",
    "Голосовой помощник",
    "Запись экрана",
    "Режим производительности",
    "Доступность",
    "Пространственный звук",
    "Игровой режим",
    "История буфера",
    "Виртуальные рабочие столы",
    "Автояркость",
    "Планировщик тем",
    "Панель виджетов",
    "Защита системы",
    "VPN",
    "Поиск устройства",
    "Системная телеметрия",
]


def create_rounded_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, theme, width=160, height=34):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=theme["window_bg"])
        self.command = command
        self.theme = theme
        self.rect = create_rounded_rect(
            self,
            2,
            2,
            width - 2,
            height - 2,
            radius=12,
            fill=theme["taskbar_bg"],
            outline=theme["accent"],
        )
        self.label = self.create_text(
            width / 2,
            height / 2,
            text=text,
            fill=theme["text"],
            font=("Segoe UI", 10, "bold"),
        )
        self.bind("<Button-1>", lambda event: self.command())
        self.bind("<Enter>", lambda event: self.itemconfig(self.rect, fill=theme["accent"]))
        self.bind("<Leave>", lambda event: self.itemconfig(self.rect, fill=theme["taskbar_bg"]))

    def update_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["window_bg"])
        self.itemconfig(self.rect, fill=theme["taskbar_bg"], outline=theme["accent"])
        self.itemconfig(self.label, fill=theme["text"])


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FS_DIR, exist_ok=True)
    os.makedirs(APPS_DIR, exist_ok=True)
    os.makedirs(STORE_DIR, exist_ok=True)


def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(default, file, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


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
        RoundedButton(buttons, "Загрузить", self.upload_file, theme, width=140).pack(pady=4)
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
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
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
    def __init__(self, master, theme, config):
        super().__init__(master, "Центр управления", theme)
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
            var = tk.BooleanVar(value=False)
            self.toggle_vars[name] = var
            row = idx // 3
            col = idx % 3
            card = tk.Frame(grid, bg=theme["taskbar_bg"], highlightbackground=theme["accent"], highlightthickness=1)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            tk.Label(card, text=name, bg=theme["taskbar_bg"], fg=theme["text"]).pack(padx=8, pady=(8, 4))
            toggle = ttk.Checkbutton(card, variable=var)
            toggle.pack(pady=(0, 8))
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)


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


class DesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_directories()
        self.config_data = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.users = load_json(USERS_PATH, DEFAULT_USERS)
        self.theme = THEMES[self.config_data.get("theme", "light")]
        self.title("Butterfly OS 13")
        self.attributes("-fullscreen", True)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.configure(bg=self.theme["desktop_bg"])
        self.desktop = tk.Canvas(self, bg=self.theme["desktop_bg"], highlightthickness=0)
        self.desktop.pack(fill="both", expand=True)
        self.taskbar = tk.Frame(self, bg=self.theme["taskbar_bg"], height=40)
        self.taskbar.place(relx=0, rely=1, anchor="sw", relwidth=1)
        self.start_button = RoundedButton(
            self.taskbar,
            "Пуск",
            self.toggle_start_menu,
            self.theme,
            width=90,
            height=30,
        )
        self.start_button.pack(side="left", padx=6, pady=4)
        self.taskbar_apps = tk.Frame(self.taskbar, bg=self.theme["taskbar_bg"])
        self.taskbar_apps.pack(side="left", padx=10)
        self.start_menu = None
        self.open_windows = {}
        self.dragging = None
        self.desktop.bind("<ButtonPress-1>", self.on_icon_press)
        self.desktop.bind("<B1-Motion>", self.on_icon_drag)
        self.desktop.bind("<ButtonRelease-1>", self.on_icon_release)
        self.desktop.bind("<Double-Button-1>", self.launch_icon)
        self.bind("<Control-l>", lambda event: self.lock_screen())
        self._build_icons()
        self.update_taskbar()
        self.boot_screen = BootScreen(self, self.theme)
        self.after(1200, self.boot_screen.destroy)
        self.after(1300, self.show_login)

    def show_login(self):
        LoginScreen(self, self.theme, self.users, self.on_login)

    def on_login(self, user):
        self.config_data["last_user"] = user
        save_json(CONFIG_PATH, self.config_data)

    def toggle_start_menu(self):
        if self.start_menu and self.start_menu.winfo_exists():
            self.start_menu.destroy()
            return
        self.start_menu = tk.Toplevel(self)
        self.start_menu.overrideredirect(True)
        self.start_menu.configure(bg=self.theme["window_bg"])
        x = 10
        y = self.winfo_height() - 300
        self.start_menu.geometry(f"220x260+{x}+{y}")
        buttons = [
            ("Проводник", lambda: self.launch_app("explorer")),
            ("Настройки", lambda: self.launch_app("settings")),
            ("Магазин приложений", lambda: self.launch_app("store")),
            ("Центр управления", lambda: self.launch_app("control")),
            ("Сменить пользователя", self.show_login),
            ("Заблокировать", self.lock_screen),
            ("Выключить", self.quit),
        ]
        for label, command in buttons:
            RoundedButton(self.start_menu, label, command, self.theme, width=190).pack(padx=8, pady=4)

    def _build_icons(self):
        self.icons = {
            "Проводник": {"app": "explorer"},
            "Настройки": {"app": "settings"},
            "Магазин приложений": {"app": "store"},
            "Центр управления": {"app": "control"},
            "Игры": {"app": "games"},
            "Медиаплеер": {"app": "media"},
            "Галерея": {"app": "gallery"},
            "Календарь": {"app": "calendar"},
            "Калькулятор": {"app": "calculator"},
            "Погода": {"app": "weather"},
            "Документы": {"app": "documents"},
        }
        for app in self.get_installed_apps():
            self.icons[app] = {"app": app}
        self._render_icons()

    def _render_icons(self):
        self.desktop.delete("icon")
        padding = 90
        col = 0
        row = 0
        for name in self.icons:
            pos = self.config_data["icon_positions"].get(name)
            if pos:
                x, y = pos
            else:
                x = 60 + col * padding
                y = 60 + row * padding
            style = ICON_STYLES.get(name, {"color": self.theme["accent"], "symbol": "🦋"})
            self.desktop.create_oval(
                x - 26,
                y - 26,
                x + 26,
                y + 26,
                fill=style["color"],
                outline=self.theme["window_bg"],
                width=2,
                tags=("icon", name),
            )
            self.desktop.create_text(
                x,
                y,
                text=style["symbol"],
                fill="white",
                font=("Segoe UI Emoji", 16),
                tags=("icon", name),
            )
            self.desktop.create_text(
                x,
                y + 42,
                text=name,
                fill=self.theme["text"],
                font=("Segoe UI", 9),
                tags=("icon", name),
            )
            col += 1
            if col >= 6:
                col = 0
                row += 1

    def on_icon_press(self, event):
        items = self.desktop.find_withtag(tk.CURRENT)
        if not items:
            return
        tags = self.desktop.gettags(items[0])
        for tag in tags:
            if tag in self.icons:
                self.dragging = {
                    "name": tag,
                    "start_x": event.x,
                    "start_y": event.y,
                }
                return

    def on_icon_drag(self, event):
        if not self.dragging:
            return
        dx = event.x - self.dragging["start_x"]
        dy = event.y - self.dragging["start_y"]
        self.desktop.move(self.dragging["name"], dx, dy)
        self.dragging["start_x"] = event.x
        self.dragging["start_y"] = event.y

    def on_icon_release(self, event):
        if not self.dragging:
            return
        name = self.dragging["name"]
        coords = self.desktop.coords(name)
        if coords:
            x = (coords[0] + coords[2]) / 2
            y = (coords[1] + coords[3]) / 2
            self.config_data["icon_positions"][name] = [x, y]
            save_json(CONFIG_PATH, self.config_data)
        self.dragging = None

    def launch_icon(self, event):
        items = self.desktop.find_withtag(tk.CURRENT)
        if not items:
            return
        tags = self.desktop.gettags(items[0])
        for tag in tags:
            if tag in self.icons:
                self.launch_app(self.icons[tag]["app"])

    def get_installed_apps(self):
        apps = []
        for entry in os.listdir(APPS_DIR):
            if entry.endswith(".butterfly"):
                apps.append(entry)
        return apps

    def update_taskbar(self):
        for widget in self.taskbar_apps.winfo_children():
            widget.destroy()
        for name in self.open_windows:
            RoundedButton(
                self.taskbar_apps,
                name,
                lambda n=name: self.focus_window(n),
                self.theme,
                width=120,
                height=28,
            ).pack(side="left", padx=4)

    def focus_window(self, name):
        window = self.open_windows.get(name)
        if window and window.winfo_exists():
            window.deiconify()
            window.lift()

    def launch_app(self, app_name):
        if app_name == "explorer":
            self._open_window("Проводник", lambda: FileExplorer(self, self.theme, FS_DIR))
            return
        if app_name == "settings":
            self._open_window(
                "Настройки",
                lambda: SettingsWindow(self, self.theme, self.config_data, self.users, self.reload_theme),
            )
            return
        if app_name == "store":
            self._open_window("Магазин приложений", lambda: AppInstaller(self, self.theme, self.refresh_apps))
            return
        if app_name == "control":
            self._open_window("Центр управления", lambda: ControlCenter(self, self.theme, self.config_data))
            return
        if app_name == "games":
            self._open_window(
                "Игры",
                lambda: GenericAppWindow(self, self.theme, "Игры", "Коллекция мини-игр Butterfly OS."),
            )
            return
        if app_name == "media":
            self._open_window(
                "Медиаплеер",
                lambda: GenericAppWindow(self, self.theme, "Медиаплеер", "Воспроизведение музыки и видео."),
            )
            return
        if app_name == "gallery":
            self._open_window(
                "Галерея",
                lambda: GenericAppWindow(self, self.theme, "Галерея", "Просмотр фото из Butterfly FS."),
            )
            return
        if app_name == "calendar":
            self._open_window(
                "Календарь",
                lambda: GenericAppWindow(self, self.theme, "Календарь", "Планирование задач и напоминаний."),
            )
            return
        if app_name == "calculator":
            self._open_window(
                "Калькулятор",
                lambda: GenericAppWindow(self, self.theme, "Калькулятор", "Быстрые вычисления."),
            )
            return
        if app_name == "weather":
            self._open_window(
                "Погода",
                lambda: GenericAppWindow(self, self.theme, "Погода", "Прогноз и текущие условия."),
            )
            return
        if app_name == "documents":
            self._open_window(
                "Документы",
                lambda: GenericAppWindow(self, self.theme, "Документы", "Управление файлами и документами."),
            )
            return
        if app_name.endswith(".butterfly"):
            self._open_window(app_name, lambda: self.run_butterfly_app(app_name))
            return

    def _open_window(self, name, builder):
        if name in self.open_windows and self.open_windows[name].winfo_exists():
            self.focus_window(name)
            return
        window = builder()
        self.open_windows[name] = window
        window.on_close = lambda n=name: self._close_window(n)
        self.update_taskbar()

    def _close_window(self, name):
        if name in self.open_windows:
            del self.open_windows[name]
        self.update_taskbar()

    def run_butterfly_app(self, app_name):
        app_path = os.path.join(APPS_DIR, app_name)
        manifest_path = os.path.join(app_path, "manifest.json")
        main_path = os.path.join(app_path, "main.py")
        if not os.path.exists(manifest_path) or not os.path.exists(main_path):
            messagebox.showerror("Butterfly OS", "Неверный пакет Butterfly.")
            return
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)
        app_window = Window(self, manifest.get("name", app_name), self.theme)
        frame = tk.Frame(app_window, bg=self.theme["window_bg"])
        frame.pack(fill="both", expand=True)
        app_globals = {"root": app_window, "frame": frame, "theme": self.theme}
        try:
            with open(main_path, "r", encoding="utf-8") as file:
                code = compile(file.read(), main_path, "exec")
                exec(code, app_globals)
        except Exception as exc:  # pragma: no cover
            tk.Label(
                frame,
                text=f"Ошибка приложения: {exc}",
                bg=self.theme["window_bg"],
                fg=self.theme["text"],
            ).pack(padx=20, pady=20)
        return app_window

    def refresh_apps(self):
        self._build_icons()

    def reload_theme(self):
        self.theme = THEMES[self.config_data.get("theme", "light")]
        save_json(CONFIG_PATH, self.config_data)
        self.configure(bg=self.theme["desktop_bg"])
        self.desktop.configure(bg=self.theme["desktop_bg"])
        self.taskbar.configure(bg=self.theme["taskbar_bg"])
        self.start_button.update_theme(self.theme)
        self.taskbar_apps.configure(bg=self.theme["taskbar_bg"])
        self._build_icons()
        self.update_taskbar()

    def lock_screen(self):
        lock = tk.Toplevel(self)
        lock.overrideredirect(True)
        lock.configure(bg=self.theme["desktop_bg"])
        lock.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        frame = tk.Frame(lock, bg=self.theme["desktop_bg"])
        frame.pack(expand=True)
        tk.Label(
            frame,
            text="Заблокировано",
            font=("Segoe UI", 20, "bold"),
            bg=self.theme["desktop_bg"],
            fg=self.theme["accent"],
        ).pack(pady=10)
        tk.Label(frame, text="Пароль", bg=self.theme["desktop_bg"], fg=self.theme["text"]).pack()
        entry = tk.Entry(frame, show="*")
        entry.pack(pady=6)

        def unlock():
            user = self.config_data.get("last_user", "admin")
            if self.users["users"].get(user, {}).get("password") == entry.get():
                lock.destroy()
            else:
                messagebox.showerror("Butterfly OS", "Неверный пароль.")

        RoundedButton(frame, "Разблокировать", unlock, self.theme, width=180).pack(pady=8)


def seed_store():
    demo_app = os.path.join(STORE_DIR, "Notes.butterfly")
    if not os.path.exists(demo_app):
        os.makedirs(demo_app, exist_ok=True)
        with open(os.path.join(demo_app, "manifest.json"), "w", encoding="utf-8") as file:
            json.dump({"name": "Заметки"}, file, indent=2)
        with open(os.path.join(demo_app, "main.py"), "w", encoding="utf-8") as file:
            file.write(
                """
import tkinter as tk

            tk.Label(frame, text='Butterfly Заметки', font=('Segoe UI', 14, 'bold'), bg=theme['window_bg'], fg=theme['text']).pack(pady=10)
            text = tk.Text(frame)
            text.pack(fill='both', expand=True, padx=10, pady=10)
"""
            )


if __name__ == "__main__":
    ensure_directories()
    seed_store()
    app = DesktopApp()
    app.mainloop()
