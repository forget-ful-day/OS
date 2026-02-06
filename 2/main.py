import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    LEFT,
    RIGHT,
    TOP,
    X,
    Y,
    Canvas,
    Entry,
    Frame,
    Label,
    Listbox,
    PhotoImage,
    StringVar,
    Tk,
    Text,
    Toplevel,
    messagebox,
    filedialog,
    ttk,
)

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageTk = None

BASE_DIR = Path(__file__).resolve().parent
FS_DIR = BASE_DIR / "butterfly_fs"
APPS_DIR = BASE_DIR / "apps"
CONFIG_PATH = BASE_DIR / "config.json"
USERS_PATH = BASE_DIR / "users.json"

APP_VERSION = "Butterfly OS 13"

THEMES = {
    "Light": {
        "bg": "#e6ecf5",
        "panel": "#ffffff",
        "text": "#1b1b1b",
        "accent": "#4b68ff",
        "taskbar": "#dbe3f3",
    },
    "Dark": {
        "bg": "#1e1f24",
        "panel": "#2a2c33",
        "text": "#f5f5f5",
        "accent": "#3b82f6",
        "taskbar": "#23242a",
    },
    "Butterfly Neon": {
        "bg": "#140b2d",
        "panel": "#221241",
        "text": "#f8f0ff",
        "accent": "#ff4dd8",
        "taskbar": "#1c1037",
    },
}

DEFAULT_CONFIG = {
    "theme": "Light",
    "icon_positions": {},
    "installed_apps": [],
}

DEFAULT_USERS = {
    "users": [
        {"username": "Butterfly", "password": "butterfly"},
    ],
    "last_user": "Butterfly",
}


@dataclass
class AppManifest:
    name: str
    entry: str
    icon: str = ""
    description: str = ""


@dataclass
class RunningApp:
    name: str
    window: Toplevel
    task_button: ttk.Button


class ConfigStore:
    def __init__(self, path: Path, default: dict):
        self.path = path
        self.data = default
        self.load()

    def load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = DEFAULT_CONFIG.copy()
        else:
            self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


class UsersStore:
    def __init__(self, path: Path, default: dict):
        self.path = path
        self.data = default
        self.load()

    def load(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = DEFAULT_USERS.copy()
        else:
            self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_user(self, username: str, password: str):
        self.data["users"].append({"username": username, "password": password})
        self.data["last_user"] = username
        self.save()


class BootScreen(Toplevel):
    def __init__(self, root, theme):
        super().__init__(root)
        self.theme = theme
        self.title("Boot")
        self.geometry("520x300")
        self.configure(bg=theme["bg"])
        self.overrideredirect(True)
        self.label = Label(
            self,
            text="Butterfly OS загрузка...",
            font=("Segoe UI", 18, "bold"),
            fg=theme["text"],
            bg=theme["bg"],
        )
        self.label.pack(pady=40)
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(pady=30, padx=60, fill=X)
        self.status = Label(
            self,
            text="Запуск системных сервисов",
            font=("Segoe UI", 11),
            fg=theme["text"],
            bg=theme["bg"],
        )
        self.status.pack(pady=10)
        self.progress.start(10)


class WindowManager:
    def __init__(self, root, taskbar, theme):
        self.root = root
        self.taskbar = taskbar
        self.theme = theme
        self.running_apps: dict[str, RunningApp] = {}

    def register(self, name: str, window: Toplevel):
        button = ttk.Button(self.taskbar, text=name, command=lambda: self.focus(name))
        button.pack(side=LEFT, padx=4, pady=4)
        self.running_apps[name] = RunningApp(name, window, button)
        window.protocol("WM_DELETE_WINDOW", lambda: self.close(name))

    def focus(self, name: str):
        app = self.running_apps.get(name)
        if not app:
            return
        app.window.deiconify()
        app.window.lift()

    def minimize(self, name: str):
        app = self.running_apps.get(name)
        if app:
            app.window.withdraw()

    def close(self, name: str):
        app = self.running_apps.pop(name, None)
        if app:
            app.task_button.destroy()
            app.window.destroy()

    def update_theme(self, theme):
        self.theme = theme
        for app in self.running_apps.values():
            app.task_button.configure(style="Taskbar.TButton")


class DesktopIcon:
    def __init__(self, canvas: Canvas, name: str, icon_text: str, command):
        self.canvas = canvas
        self.name = name
        self.command = command
        self.icon_text = icon_text
        self.frame = Frame(canvas, bg="", highlightthickness=0)
        self.icon_label = Label(self.frame, text=icon_text, font=("Segoe UI", 20))
        self.text_label = Label(self.frame, text=name, font=("Segoe UI", 10))
        self.icon_label.pack()
        self.text_label.pack()
        self.window_id = canvas.create_window(0, 0, window=self.frame, anchor="nw")
        self._drag_data = None
        for widget in (self.frame, self.icon_label, self.text_label):
            widget.bind("<Button-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Double-Button-1>", lambda _event: self.command())

    def move_to(self, x: int, y: int):
        self.canvas.coords(self.window_id, x, y)

    def _on_press(self, event):
        self._drag_data = (event.x_root, event.y_root)

    def _on_drag(self, event):
        if not self._drag_data:
            return
        dx = event.x_root - self._drag_data[0]
        dy = event.y_root - self._drag_data[1]
        x, y = self.canvas.coords(self.window_id)
        self.canvas.coords(self.window_id, x + dx, y + dy)
        self._drag_data = (event.x_root, event.y_root)

    def _on_release(self, _event):
        self._drag_data = None

    def get_position(self):
        x, y = self.canvas.coords(self.window_id)
        return int(x), int(y)


class ButterflyOS:
    def __init__(self):
        FS_DIR.mkdir(exist_ok=True)
        APPS_DIR.mkdir(exist_ok=True)
        self.config = ConfigStore(CONFIG_PATH, DEFAULT_CONFIG.copy())
        self.users = UsersStore(USERS_PATH, DEFAULT_USERS.copy())
        self.ensure_default_apps()
        self.theme_name = self.config.data.get("theme", "Light")
        self.theme = THEMES[self.theme_name]
        self.root = Tk()
        self.root.title(APP_VERSION)
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=self.theme["bg"])
        self.root.bind("<Escape>", lambda _e: self.root.attributes("-fullscreen", False))
        self.root.bind("<F11>", lambda _e: self.root.attributes("-fullscreen", True))
        self.root.bind("<Control-l>", lambda _e: self.lock_screen())
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.window_manager = None
        self.desktop_icons: dict[str, DesktopIcon] = {}
        self.current_user = None
        self.login_screen()

    def login_screen(self):
        self.clear_root()
        self.root.configure(bg=self.theme["bg"])
        Label(
            self.root,
            text=APP_VERSION,
            font=("Segoe UI", 24, "bold"),
            fg=self.theme["text"],
            bg=self.theme["bg"],
        ).pack(pady=40)
        container = Frame(self.root, bg=self.theme["bg"])
        container.pack(pady=20)
        Label(
            container,
            text="Выберите пользователя",
            font=("Segoe UI", 12),
            fg=self.theme["text"],
            bg=self.theme["bg"],
        ).pack(pady=10)
        users_frame = Frame(container, bg=self.theme["bg"])
        users_frame.pack()
        self.user_var = StringVar(value=self.users.data.get("last_user"))
        for user in self.users.data["users"]:
            ttk.Radiobutton(
                users_frame,
                text=user["username"],
                variable=self.user_var,
                value=user["username"],
            ).pack(anchor="w", pady=2)
        Label(container, text="Пароль", bg=self.theme["bg"], fg=self.theme["text"]).pack(pady=5)
        self.password_entry = Entry(container, show="*", width=30)
        self.password_entry.pack(pady=5)
        ttk.Button(container, text="Войти", command=self.attempt_login).pack(pady=10)

    def on_exit(self):
        if self.desktop_icons:
            self.save_icon_positions()
        self.root.destroy()

    def attempt_login(self):
        username = self.user_var.get()
        password = self.password_entry.get()
        for user in self.users.data["users"]:
            if user["username"] == username and user["password"] == password:
                self.current_user = username
                self.users.data["last_user"] = username
                self.users.save()
                self.show_boot_then_desktop()
                return
        messagebox.showerror("Ошибка", "Неверный пароль")

    def show_boot_then_desktop(self):
        boot = BootScreen(self.root, self.theme)
        boot.update()
        self.root.after(1500, boot.destroy)
        self.root.after(1600, self.load_desktop)

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def load_desktop(self):
        self.clear_root()
        self.root.configure(bg=self.theme["bg"])
        self.desktop_canvas = Canvas(self.root, bg=self.theme["bg"], highlightthickness=0)
        self.desktop_canvas.pack(fill=BOTH, expand=True)
        self.taskbar = Frame(self.root, bg=self.theme["taskbar"], height=40)
        self.taskbar.pack(side=BOTTOM, fill=X)
        ttk.Button(self.taskbar, text="Пуск", command=self.open_start_menu).pack(side=LEFT, padx=8)
        self.window_manager = WindowManager(self.root, self.taskbar, self.theme)
        self.load_desktop_icons()
        self.render_clock()

    def render_clock(self):
        self.clock_label = Label(self.taskbar, bg=self.theme["taskbar"], fg=self.theme["text"])
        self.clock_label.pack(side=RIGHT, padx=12)
        self.update_clock()

    def update_clock(self):
        self.clock_label.configure(text=time.strftime("%H:%M"))
        self.root.after(10000, self.update_clock)

    def load_desktop_icons(self):
        self.desktop_icons.clear()
        icons = [
            ("Проводник", "📁", self.open_file_explorer),
            ("Настройки", "⚙️", self.open_settings),
            ("Butterfly Store", "🦋", self.open_app_store),
            ("Игры", "🎮", self.open_games),
            ("Фото", "🖼️", self.open_photos_app),
            ("Тексты", "📝", self.open_text_editor),
        ]
        positions = self.config.data.get("icon_positions", {})
        x, y = 40, 40
        for name, icon, command in icons:
            desktop_icon = DesktopIcon(self.desktop_canvas, name, icon, command)
            pos = positions.get(name, [x, y])
            desktop_icon.move_to(pos[0], pos[1])
            self.desktop_icons[name] = desktop_icon
            y += 110

        for manifest in self.load_installed_manifests():
            app_name = manifest.name
            desktop_icon = DesktopIcon(
                self.desktop_canvas,
                app_name,
                manifest.icon or "🧩",
                lambda m=manifest: self.launch_butterfly_app(m),
            )
            pos = positions.get(app_name, [x + 180, 40])
            desktop_icon.move_to(pos[0], pos[1])
            self.desktop_icons[app_name] = desktop_icon

    def save_icon_positions(self):
        positions = {name: icon.get_position() for name, icon in self.desktop_icons.items()}
        self.config.data["icon_positions"] = positions
        self.config.save()

    def open_start_menu(self):
        menu = Toplevel(self.root)
        menu.title("Пуск")
        menu.geometry("260x420+20+300")
        menu.configure(bg=self.theme["panel"])
        menu.transient(self.root)
        menu.grab_set()
        ttk.Button(menu, text="Проводник", command=self.open_file_explorer).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Настройки", command=self.open_settings).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Установщик приложений", command=self.open_installer).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Butterfly Store", command=self.open_app_store).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Сменить пользователя", command=self.switch_user).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Заблокировать (Win+L)", command=self.lock_screen).pack(fill=X, padx=10, pady=6)
        ttk.Button(menu, text="Выход", command=self.login_screen).pack(fill=X, padx=10, pady=6)

    def switch_user(self):
        self.save_icon_positions()
        self.login_screen()

    def lock_screen(self):
        lock = Toplevel(self.root)
        lock.title("Экран блокировки")
        lock.attributes("-fullscreen", True)
        lock.configure(bg=self.theme["bg"])
        Label(
            lock,
            text="Экран блокировки",
            font=("Segoe UI", 24, "bold"),
            fg=self.theme["text"],
            bg=self.theme["bg"],
        ).pack(pady=40)
        Label(
            lock,
            text=f"Пользователь: {self.current_user}",
            font=("Segoe UI", 12),
            fg=self.theme["text"],
            bg=self.theme["bg"],
        ).pack(pady=10)
        password_entry = Entry(lock, show="*", width=30)
        password_entry.pack(pady=10)

        def unlock():
            password = password_entry.get()
            for user in self.users.data["users"]:
                if user["username"] == self.current_user and user["password"] == password:
                    lock.destroy()
                    return
            messagebox.showerror("Ошибка", "Неверный пароль")

        ttk.Button(lock, text="Разблокировать", command=unlock).pack(pady=10)

    def themed_window(self, title: str, size: str = "700x450"):
        window = Toplevel(self.root)
        window.title(title)
        window.geometry(size)
        window.configure(bg=self.theme["panel"])
        window.transient(self.root)
        window.lift()
        self.window_manager.register(title, window)
        header = Frame(window, bg=self.theme["accent"], height=36)
        header.pack(fill=X)
        Label(
            header,
            text=title,
            bg=self.theme["accent"],
            fg="white",
            font=("Segoe UI", 11, "bold"),
        ).pack(side=LEFT, padx=10)
        ttk.Button(
            header,
            text="_",
            width=3,
            command=lambda: self.window_manager.minimize(title),
        ).pack(side=RIGHT, padx=4, pady=4)
        ttk.Button(
            header,
            text="X",
            width=3,
            command=lambda: self.window_manager.close(title),
        ).pack(side=RIGHT, padx=4, pady=4)
        return window

    def open_file_explorer(self):
        window = self.themed_window("Проводник")
        left = Frame(window, bg=self.theme["panel"])
        left.pack(side=LEFT, fill=Y)
        right = Frame(window, bg=self.theme["panel"])
        right.pack(side=RIGHT, fill=BOTH, expand=True)
        listbox = Listbox(left, width=30)
        listbox.pack(side=LEFT, fill=Y, padx=5, pady=5)
        files = sorted([p.name for p in FS_DIR.iterdir()])
        for name in files:
            listbox.insert("end", name)

        def open_selected():
            selection = listbox.curselection()
            if not selection:
                return
            filename = listbox.get(selection[0])
            self.open_file(FS_DIR / filename)

        ttk.Button(left, text="Открыть", command=open_selected).pack(pady=6)
        ttk.Button(left, text="Создать файл", command=self.create_file).pack(pady=6)
        ttk.Button(left, text="Обновить", command=self.refresh_explorer).pack(pady=6)
        Label(right, text="Выберите файл для просмотра", bg=self.theme["panel"], fg=self.theme["text"]).pack(
            pady=30
        )

    def refresh_explorer(self):
        self.open_file_explorer()

    def create_file(self):
        filename = filedialog.asksaveasfilename(initialdir=str(FS_DIR))
        if not filename:
            return
        Path(filename).write_text("", encoding="utf-8")

    def open_file(self, path: Path):
        if path.suffix.lower() in {".txt", ".md", ".py", ".json"}:
            self.open_text_file(path)
        elif path.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg"}:
            self.open_image_file(path)
        else:
            messagebox.showinfo("Файл", f"Неизвестный формат: {path.name}")

    def open_text_file(self, path: Path):
        window = self.themed_window(f"Текст: {path.name}")
        text = Text(window)
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", path.read_text(encoding="utf-8"))

    def open_image_file(self, path: Path):
        window = self.themed_window(f"Фото: {path.name}")
        canvas = Canvas(window, bg=self.theme["panel"])
        canvas.pack(fill=BOTH, expand=True)
        if Image:
            image = Image.open(path)
            image.thumbnail((600, 400))
            tk_image = ImageTk.PhotoImage(image)
        else:
            tk_image = PhotoImage(file=path)
        canvas.image = tk_image
        canvas.create_image(20, 20, anchor="nw", image=tk_image)

    def open_settings(self):
        window = self.themed_window("Настройки", "640x480")
        tabs = ttk.Notebook(window)
        tabs.pack(fill=BOTH, expand=True, padx=10, pady=10)
        theme_frame = Frame(tabs, bg=self.theme["panel"])
        users_frame = Frame(tabs, bg=self.theme["panel"])
        tabs.add(theme_frame, text="Темы")
        tabs.add(users_frame, text="Пользователи")

        Label(theme_frame, text="Выберите тему", bg=self.theme["panel"], fg=self.theme["text"]).pack(pady=10)
        theme_var = StringVar(value=self.theme_name)
        for name in THEMES:
            ttk.Radiobutton(theme_frame, text=name, variable=theme_var, value=name).pack(anchor="w", padx=20)

        def apply_theme():
            self.theme_name = theme_var.get()
            self.theme = THEMES[self.theme_name]
            self.config.data["theme"] = self.theme_name
            self.config.save()
            self.load_desktop()

        ttk.Button(theme_frame, text="Применить", command=apply_theme).pack(pady=10)

        Label(users_frame, text="Создать пользователя", bg=self.theme["panel"], fg=self.theme["text"]).pack(pady=10)
        new_user = Entry(users_frame, width=25)
        new_user.pack(pady=5)
        new_pass = Entry(users_frame, show="*", width=25)
        new_pass.pack(pady=5)

        def add_user():
            if not new_user.get() or not new_pass.get():
                messagebox.showwarning("Внимание", "Введите имя и пароль")
                return
            self.users.add_user(new_user.get(), new_pass.get())
            messagebox.showinfo("Готово", "Пользователь добавлен")

        ttk.Button(users_frame, text="Создать", command=add_user).pack(pady=10)

    def open_installer(self):
        window = self.themed_window("Установщик приложений", "520x320")
        Label(
            window,
            text="Выберите пакет .butterfly (папка с manifest.json)",
            bg=self.theme["panel"],
            fg=self.theme["text"],
        ).pack(pady=10)

        def install():
            folder = filedialog.askdirectory()
            if not folder:
                return
            folder_path = Path(folder)
            manifest_path = folder_path / "manifest.json"
            if not manifest_path.exists():
                messagebox.showerror("Ошибка", "manifest.json не найден")
                return
            dest = APPS_DIR / folder_path.name
            if dest.exists():
                messagebox.showwarning("Уже установлено", "Приложение уже установлено")
                return
            shutil.copytree(folder_path, dest)
            self.config.data["installed_apps"].append(folder_path.name)
            self.config.save()
            messagebox.showinfo("Установлено", "Приложение установлено")
            self.load_desktop()

        ttk.Button(window, text="Установить", command=install).pack(pady=10)

    def load_installed_manifests(self):
        manifests = []
        for name in self.config.data.get("installed_apps", []):
            manifest_path = APPS_DIR / name / "manifest.json"
            if not manifest_path.exists():
                continue
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifests.append(AppManifest(**data))
        return manifests

    def launch_butterfly_app(self, manifest: AppManifest):
        app_window = self.themed_window(manifest.name, "700x450")
        app_frame = Frame(app_window, bg=self.theme["panel"])
        app_frame.pack(fill=BOTH, expand=True)
        script_path = APPS_DIR / manifest.name / manifest.entry
        if not script_path.exists():
            Label(app_frame, text="Файл приложения не найден", bg=self.theme["panel"], fg=self.theme["text"]).pack(
                pady=20
            )
            return
        namespace = {"root": app_frame, "theme": self.theme, "FS_DIR": FS_DIR}
        try:
            exec(script_path.read_text(encoding="utf-8"), namespace)
        except Exception as exc:  # pragma: no cover
            Label(app_frame, text=f"Ошибка запуска: {exc}", bg=self.theme["panel"], fg=self.theme["text"]).pack(
                pady=20
            )

    def open_app_store(self):
        window = self.themed_window("Butterfly Store", "600x380")
        Label(window, text="Рекомендуемые приложения", bg=self.theme["panel"], fg=self.theme["text"]).pack(
            pady=10
        )
        store = Frame(window, bg=self.theme["panel"])
        store.pack(fill=BOTH, expand=True)
        apps = [
            ("Galaxy Clock", "Часы с космической темой"),
            ("Neon Notes", "Блокнот в стиле Butterfly"),
        ]

        for app_name, desc in apps:
            item = Frame(store, bg=self.theme["panel"], highlightbackground=self.theme["accent"], highlightthickness=1)
            item.pack(fill=X, padx=10, pady=6)
            Label(item, text=app_name, bg=self.theme["panel"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).pack(
                side=LEFT, padx=10
            )
            Label(item, text=desc, bg=self.theme["panel"], fg=self.theme["text"]).pack(side=LEFT, padx=10)
            ttk.Button(item, text="Установить", command=self.open_installer).pack(side=RIGHT, padx=10)

    def open_games(self):
        window = self.themed_window("Игры", "500x360")
        Label(window, text="Предустановленные игры", bg=self.theme["panel"], fg=self.theme["text"]).pack(pady=10)
        ttk.Button(window, text="Угадай число", command=self.launch_guess_game).pack(pady=6)

    def launch_guess_game(self):
        window = self.themed_window("Угадай число", "420x300")
        import random

        number = random.randint(1, 50)
        Label(window, text="Я загадал число от 1 до 50", bg=self.theme["panel"], fg=self.theme["text"]).pack(pady=10)
        entry = Entry(window)
        entry.pack(pady=5)
        result = Label(window, text="", bg=self.theme["panel"], fg=self.theme["text"])
        result.pack(pady=5)

        def check():
            try:
                guess = int(entry.get())
            except ValueError:
                result.configure(text="Введите число")
                return
            if guess == number:
                result.configure(text="Верно! 🎉")
            elif guess < number:
                result.configure(text="Слишком мало")
            else:
                result.configure(text="Слишком много")

        ttk.Button(window, text="Проверить", command=check).pack(pady=6)

    def open_text_editor(self):
        window = self.themed_window("Тексты", "640x480")
        text = Text(window)
        text.pack(fill=BOTH, expand=True)

        def save_text():
            path = filedialog.asksaveasfilename(initialdir=str(FS_DIR), defaultextension=".txt")
            if not path:
                return
            Path(path).write_text(text.get("1.0", "end"), encoding="utf-8")

        ttk.Button(window, text="Сохранить", command=save_text).pack(pady=6)

    def open_photos_app(self):
        window = self.themed_window("Фото", "640x480")
        Label(window, text="Открыть изображение", bg=self.theme["panel"], fg=self.theme["text"]).pack(pady=10)

        def open_photo():
            path = filedialog.askopenfilename(initialdir=str(FS_DIR))
            if not path:
                return
            self.open_image_file(Path(path))

        ttk.Button(window, text="Открыть", command=open_photo).pack(pady=6)

    def ensure_default_apps(self):
        sample_app = APPS_DIR / "ButterflyNotes"
        if not sample_app.exists():
            sample_app.mkdir(parents=True, exist_ok=True)
            (sample_app / "manifest.json").write_text(
                json.dumps(
                    {
                        "name": "ButterflyNotes",
                        "entry": "main.py",
                        "icon": "📝",
                        "description": "Мини-блокнот",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (sample_app / "main.py").write_text(
                \"\"\"\nfrom tkinter import BOTH, Text, Label\n\nLabel(root, text=\"ButterflyNotes\", bg=theme[\"panel\"], fg=theme[\"text\"], font=(\"Segoe UI\", 14, \"bold\")).pack(pady=6)\ntext = Text(root)\ntext.pack(fill=BOTH, expand=True, padx=10, pady=10)\n\"\"\",\n                encoding="utf-8",
            )
        if "ButterflyNotes" not in self.config.data.get("installed_apps", []):
            self.config.data.setdefault("installed_apps", []).append("ButterflyNotes")
            self.config.save()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    ButterflyOS().root.mainloop()
