import json
import os
import tkinter as tk
from tkinter import messagebox

from .config import (
    APPS_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    DEFAULT_USERS,
    FS_DIR,
    ICON_STYLES,
    THEMES,
    USERS_PATH,
    ensure_directories,
    load_json,
    save_json,
)
from .ui_components import RoundedButton
from .windows import (
    AppInstaller,
    BootScreen,
    ControlCenter,
    FileExplorer,
    GenericAppWindow,
    LoginScreen,
    SettingsWindow,
    Window,
)


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
