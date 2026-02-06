import base64
import json
import os
import shutil
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "butterfly_data")
FS_DIR = os.path.join(DATA_DIR, "butterfly_fs")
APPS_DIR = os.path.join(DATA_DIR, "apps")
STORE_DIR = os.path.join(BASE_DIR, "store_packages")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
ICON_POSITIONS_FILE = os.path.join(DATA_DIR, "icon_positions.json")
INSTALLED_APPS_FILE = os.path.join(DATA_DIR, "installed_apps.json")

THEMES = {
    "Light": {
        "bg": "#e9eef6",
        "fg": "#1f2a44",
        "accent": "#4a6fa5",
        "taskbar": "#ffffff",
        "window": "#ffffff",
    },
    "Dark": {
        "bg": "#1f1f1f",
        "fg": "#f2f2f2",
        "accent": "#6ca0ff",
        "taskbar": "#2a2a2a",
        "window": "#2f2f2f",
    },
    "Butterfly Neon": {
        "bg": "#0b0020",
        "fg": "#f7e6ff",
        "accent": "#ff6ec7",
        "taskbar": "#160033",
        "window": "#1d0044",
    },
}

DEFAULT_USERS = {
    "users": [
        {"username": "Admin", "password": "admin"}
    ]
}

DEFAULT_SETTINGS = {
    "theme": "Light",
    "last_user": "Admin"
}

SAMPLE_TEXT = """Добро пожаловать в Butterfly OS 13!\n\nЭто пример текстового файла внутри файловой системы."""

SAMPLE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAAAQCAYAAAB9Q+uLAAAACXBIWXMAAAsT"
    "AAALEwEAmpwYAAABF0lEQVR4nO2WsUoDQRBFn9Z0g0IY0k7B6gC6Cq1E0R7A"
    "gM2Q0m8g0eYJm2KDoZy1gYH8rCq2xC1tZpJdXf2e/OGB7vY6P8z7n0wEqBf5"
    "m0Q40sQ3uEDwX4xQh3yMEu4ARc2O7j0o6zUe0mH4oY4p4yC3gQGdZBk1N3kG"
    "oDr3b2o3gLckV+1fI3r6A6GoGzq2B3V7iQYc2tNEqTa4d7M1k1sN4PzV5x2S"
    "C2T7Hqp5s8u9BkOV0n4S8IBf0C9QqP7qYQ4N5G5uKxC4+Oe3qX6o3N9bH7z4"
    "OAw/2Q9v9z8Cj2sYbqg9Gq8AAAAASUVORK5CYII="
)


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FS_DIR, exist_ok=True)
    os.makedirs(APPS_DIR, exist_ok=True)

    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, DEFAULT_USERS)

    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, DEFAULT_SETTINGS)

    if not os.path.exists(ICON_POSITIONS_FILE):
        save_json(ICON_POSITIONS_FILE, {})

    if not os.path.exists(INSTALLED_APPS_FILE):
        save_json(INSTALLED_APPS_FILE, [])

    documents = os.path.join(FS_DIR, "Documents")
    pictures = os.path.join(FS_DIR, "Pictures")
    os.makedirs(documents, exist_ok=True)
    os.makedirs(pictures, exist_ok=True)

    sample_text_path = os.path.join(documents, "welcome.txt")
    if not os.path.exists(sample_text_path):
        with open(sample_text_path, "w", encoding="utf-8") as handle:
            handle.write(SAMPLE_TEXT)

    sample_image_path = os.path.join(pictures, "butterfly.png")
    if not os.path.exists(sample_image_path):
        image_bytes = base64.b64decode(SAMPLE_PNG_BASE64)
        with open(sample_image_path, "wb") as handle:
            handle.write(image_bytes)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


@dataclass
class AppMeta:
    app_id: str
    name: str
    icon: str
    handler: callable


class BootScreen(tk.Toplevel):
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete = on_complete
        self.configure(bg="#0b0020")
        self.geometry("640x360")
        self.overrideredirect(True)
        label = tk.Label(self, text="Butterfly OS 13", fg="#ff6ec7", bg="#0b0020", font=("Segoe UI", 24, "bold"))
        label.pack(expand=True)
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=60, pady=40)
        self.progress_value = 0
        self.animate()

    def animate(self):
        self.progress_value += 5
        self.progress["value"] = self.progress_value
        if self.progress_value >= 100:
            self.after(300, self.finish)
        else:
            self.after(60, self.animate)

    def finish(self):
        self.destroy()
        self.on_complete()


class LoginScreen(tk.Frame):
    def __init__(self, master, on_login):
        super().__init__(master)
        self.on_login = on_login
        self.configure(bg="#101326")
        self.pack(fill="both", expand=True)
        self.users = load_json(USERS_FILE, DEFAULT_USERS)["users"]

        title = tk.Label(self, text="Выберите пользователя", fg="#f7e6ff", bg="#101326", font=("Segoe UI", 20, "bold"))
        title.pack(pady=20)

        self.user_var = tk.StringVar(value=self.users[0]["username"])
        for user in self.users:
            option = tk.Radiobutton(
                self,
                text=user["username"],
                variable=self.user_var,
                value=user["username"],
                fg="#f7e6ff",
                bg="#101326",
                selectcolor="#24124a",
                font=("Segoe UI", 12)
            )
            option.pack(anchor="w", padx=80)

        password_label = tk.Label(self, text="Пароль", fg="#f7e6ff", bg="#101326", font=("Segoe UI", 12))
        password_label.pack(pady=(20, 5))
        self.password_entry = tk.Entry(self, show="*", font=("Segoe UI", 12))
        self.password_entry.pack()

        button = tk.Button(self, text="Войти", command=self.handle_login, bg="#ff6ec7", fg="#0b0020", font=("Segoe UI", 12, "bold"))
        button.pack(pady=20)

    def handle_login(self):
        username = self.user_var.get()
        password = self.password_entry.get()
        for user in self.users:
            if user["username"] == username and user["password"] == password:
                settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
                settings["last_user"] = username
                save_json(SETTINGS_FILE, settings)
                self.on_login(username)
                return
        messagebox.showerror("Ошибка", "Неверный пароль")


class DesktopIcon(tk.Frame):
    def __init__(self, master, app_meta, on_open, theme):
        super().__init__(master, bg=theme["bg"], bd=0, highlightthickness=0)
        self.app_meta = app_meta
        self.on_open = on_open
        self.theme = theme
        self.label_icon = tk.Label(self, text=app_meta.icon, bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 20))
        self.label_text = tk.Label(self, text=app_meta.name, bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10))
        self.label_icon.pack()
        self.label_text.pack()
        self.bind_events()

    def bind_events(self):
        for widget in (self, self.label_icon, self.label_text):
            widget.bind("<Double-Button-1>", lambda _event: self.on_open(self.app_meta))
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)
            widget.bind("<ButtonRelease-1>", self.stop_drag)

    def start_drag(self, event):
        self._drag_start = (event.x, event.y)

    def drag(self, event):
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.place(x=x, y=y)

    def stop_drag(self, _event):
        if hasattr(self.master, "save_icon_positions"):
            self.master.save_icon_positions()


class Window(tk.Frame):
    def __init__(self, master, title, on_close, theme, on_minimize, app_id):
        super().__init__(master, bg=theme["window"], bd=2, relief="raised")
        self.theme = theme
        self.on_close = on_close
        self.on_minimize = on_minimize
        self.app_id = app_id
        self.title_bar = tk.Frame(self, bg=theme["accent"], height=28)
        self.title_bar.pack(fill="x")
        self.title_label = tk.Label(self.title_bar, text=title, bg=theme["accent"], fg="#ffffff")
        self.title_label.pack(side="left", padx=10)
        self.buttons = tk.Frame(self.title_bar, bg=theme["accent"])
        self.buttons.pack(side="right")
        minimize_btn = tk.Button(self.buttons, text="—", command=self.minimize, bg=theme["accent"], fg="#ffffff", bd=0, width=3)
        close_btn = tk.Button(self.buttons, text="✕", command=self.close, bg=theme["accent"], fg="#ffffff", bd=0, width=3)
        minimize_btn.pack(side="left", padx=2)
        close_btn.pack(side="left", padx=2)
        self.content = tk.Frame(self, bg=theme["window"])
        self.content.pack(fill="both", expand=True)
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.move)

    def start_move(self, event):
        self._move_start = (event.x, event.y)

    def move(self, event):
        dx = event.x - self._move_start[0]
        dy = event.y - self._move_start[1]
        self.place(x=self.winfo_x() + dx, y=self.winfo_y() + dy)

    def close(self):
        self.on_close(self)

    def minimize(self):
        self.on_minimize(self)


class Desktop(tk.Frame):
    def __init__(self, master, username, on_logout):
        super().__init__(master)
        self.master = master
        self.username = username
        self.on_logout = on_logout
        self.apps = {}
        self.running_windows = {}
        self.minimized_windows = {}
        self.load_state()

        self.theme = THEMES[self.settings["theme"]]
        self.configure(bg=self.theme["bg"])
        self.pack(fill="both", expand=True)

        self.desktop_area = tk.Frame(self, bg=self.theme["bg"])
        self.desktop_area.pack(fill="both", expand=True)

        self.taskbar = tk.Frame(self, bg=self.theme["taskbar"], height=40)
        self.taskbar.pack(fill="x", side="bottom")
        self.start_button = tk.Button(self.taskbar, text="🦋", command=self.toggle_start_menu, bg=self.theme["accent"], fg="#ffffff", bd=0, width=4)
        self.start_button.pack(side="left", padx=6, pady=6)

        self.taskbar_apps = tk.Frame(self.taskbar, bg=self.theme["taskbar"])
        self.taskbar_apps.pack(side="left", padx=6)

        self.clock_label = tk.Label(self.taskbar, text="", bg=self.theme["taskbar"], fg=self.theme["fg"])
        self.clock_label.pack(side="right", padx=10)

        self.start_menu = None
        self.bind_shortcuts()
        self.load_apps()
        self.render_icons()
        self.update_clock()

    def bind_shortcuts(self):
        self.master.bind("<Control-L>", lambda _event: self.lock_screen())

    def lock_screen(self):
        lock = tk.Frame(self.master, bg="#0b0020")
        lock.place(relwidth=1, relheight=1)
        label = tk.Label(lock, text="Экран заблокирован", fg="#ff6ec7", bg="#0b0020", font=("Segoe UI", 18, "bold"))
        label.pack(pady=40)
        password_entry = tk.Entry(lock, show="*", font=("Segoe UI", 12))
        password_entry.pack()

        def unlock():
            password = password_entry.get()
            users = load_json(USERS_FILE, DEFAULT_USERS)["users"]
            for user in users:
                if user["username"] == self.username and user["password"] == password:
                    lock.destroy()
                    return
            messagebox.showerror("Ошибка", "Неверный пароль")

        unlock_button = tk.Button(lock, text="Разблокировать", command=unlock, bg="#ff6ec7", fg="#0b0020")
        unlock_button.pack(pady=20)

    def update_clock(self):
        now = tk.StringVar()
        now.set(self.master.tk.call("clock", "format", self.master.tk.call("clock", "seconds"), "-format", "%H:%M"))
        self.clock_label.configure(text=now.get())
        self.after(60000, self.update_clock)

    def load_state(self):
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.icon_positions = load_json(ICON_POSITIONS_FILE, {}).get(self.username, {})

    def save_icon_positions(self):
        positions_data = load_json(ICON_POSITIONS_FILE, {})
        positions_data[self.username] = {}
        for app_id, icon in self.apps.items():
            positions_data[self.username][app_id] = {"x": icon.winfo_x(), "y": icon.winfo_y()}
        save_json(ICON_POSITIONS_FILE, positions_data)

    def load_apps(self):
        self.registry = {
            "explorer": AppMeta("explorer", "Проводник", "📁", self.open_explorer),
            "settings": AppMeta("settings", "Настройки", "⚙️", self.open_settings),
            "text_viewer": AppMeta("text_viewer", "Текст", "📝", self.open_text_viewer),
            "image_viewer": AppMeta("image_viewer", "Фото", "🖼️", self.open_image_viewer),
            "game": AppMeta("game", "Игра", "🎮", self.open_game),
            "app_store": AppMeta("app_store", "App Store", "🛒", self.open_app_store),
            "installer": AppMeta("installer", "Установщик", "⬇️", self.open_installer),
        }

        installed = load_json(INSTALLED_APPS_FILE, [])
        for package in installed:
            self.registry[package["app_id"]] = AppMeta(
                package["app_id"],
                package["name"],
                package.get("icon", "🦋"),
                lambda window, app_id=package["app_id"]: self.open_butterfly_app(window, app_id)
            )

    def render_icons(self):
        for child in self.desktop_area.winfo_children():
            child.destroy()
        self.apps = {}
        x, y = 40, 40
        for app_id, meta in self.registry.items():
            icon = DesktopIcon(self.desktop_area, meta, self.open_app, self.theme)
            pos = self.icon_positions.get(app_id)
            if pos:
                icon.place(x=pos["x"], y=pos["y"])
            else:
                icon.place(x=x, y=y)
                y += 100
                if y > 400:
                    y = 40
                    x += 120
            self.apps[app_id] = icon

    def toggle_start_menu(self):
        if self.start_menu and self.start_menu.winfo_exists():
            self.start_menu.destroy()
            self.start_menu = None
            return

        self.start_menu = tk.Toplevel(self.master)
        self.start_menu.overrideredirect(True)
        self.start_menu.configure(bg=self.theme["window"])
        x = self.start_button.winfo_rootx()
        y = self.start_button.winfo_rooty() - 260
        self.start_menu.geometry(f"260x260+{x}+{y}")

        title = tk.Label(self.start_menu, text="Пуск", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 12, "bold"))
        title.pack(pady=10)

        for meta in self.registry.values():
            item = tk.Button(
                self.start_menu,
                text=f"{meta.icon} {meta.name}",
                anchor="w",
                bg=self.theme["window"],
                fg=self.theme["fg"],
                bd=0,
                command=lambda m=meta: self.open_app(m)
            )
            item.pack(fill="x", padx=12, pady=2)

    def open_app(self, app_meta):
        if app_meta.app_id in self.running_windows:
            self.focus_window(app_meta.app_id)
            return

        window = Window(
            self.desktop_area,
            app_meta.name,
            on_close=self.close_window,
            theme=self.theme,
            on_minimize=self.minimize_window,
            app_id=app_meta.app_id
        )
        window.place(x=0, y=0, relwidth=1, relheight=1)
        self.running_windows[app_meta.app_id] = window
        self.add_taskbar_item(app_meta)
        app_meta.handler(window)

    def focus_window(self, app_id):
        window = self.running_windows.get(app_id)
        if window:
            window.lift()

    def close_window(self, window):
        app_id = window.app_id
        if app_id in self.running_windows:
            del self.running_windows[app_id]
        if app_id in self.minimized_windows:
            del self.minimized_windows[app_id]
        window.destroy()
        for widget in self.taskbar_apps.winfo_children():
            if getattr(widget, "app_id", None) == app_id:
                widget.destroy()

    def minimize_window(self, window):
        window.place_forget()
        self.minimized_windows[window.app_id] = window

    def restore_window(self, app_id):
        window = self.minimized_windows.pop(app_id, None)
        if window:
            window.place(x=0, y=0, relwidth=1, relheight=1)
            window.lift()

    def add_taskbar_item(self, meta):
        button = tk.Button(
            self.taskbar_apps,
            text=meta.icon,
            bg=self.theme["taskbar"],
            fg=self.theme["fg"],
            bd=0,
            command=lambda app_id=meta.app_id: self.restore_window(app_id)
        )
        button.app_id = meta.app_id
        button.pack(side="left", padx=4)

    def open_explorer(self, window):
        container = window.content
        path_var = tk.StringVar(value=FS_DIR)
        path_entry = tk.Entry(container, textvariable=path_var)
        path_entry.pack(fill="x", padx=10, pady=5)
        listbox = tk.Listbox(container)
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        def load_dir(path):
            listbox.delete(0, tk.END)
            for item in os.listdir(path):
                listbox.insert(tk.END, item)

        def open_item(event=None):
            selection = listbox.curselection()
            if not selection:
                return
            item = listbox.get(selection[0])
            new_path = os.path.join(path_var.get(), item)
            if os.path.isdir(new_path):
                path_var.set(new_path)
                load_dir(new_path)
            else:
                self.open_file(new_path)

        def go_up():
            current = path_var.get()
            parent = os.path.dirname(current)
            if os.path.commonpath([parent, FS_DIR]) == FS_DIR:
                path_var.set(parent)
                load_dir(parent)

        up_button = tk.Button(container, text="⬆️", command=go_up)
        up_button.pack(anchor="w", padx=10)
        listbox.bind("<Double-Button-1>", open_item)
        load_dir(path_var.get())

    def open_file(self, path):
        _, ext = os.path.splitext(path)
        if ext.lower() in {".txt", ".md"}:
            self.open_text_viewer(None, path)
        elif ext.lower() in {".png", ".gif"}:
            self.open_image_viewer(None, path)
        else:
            messagebox.showinfo("Открыть", "Неизвестный формат")

    def open_text_viewer(self, window, file_path=None):
        if window is None:
            meta = self.registry["text_viewer"]
            self.open_app(meta)
            window = self.running_windows["text_viewer"]
        content = window.content
        text = tk.Text(content)
        text.pack(fill="both", expand=True)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as handle:
                text.insert("1.0", handle.read())

    def open_image_viewer(self, window, file_path=None):
        if window is None:
            meta = self.registry["image_viewer"]
            self.open_app(meta)
            window = self.running_windows["image_viewer"]
        content = window.content
        label = tk.Label(content, bg=self.theme["window"])
        label.pack(fill="both", expand=True)
        if file_path:
            image = tk.PhotoImage(file=file_path)
            label.image = image
            label.configure(image=image)

    def open_game(self, window):
        content = window.content
        label = tk.Label(content, text="Мини-игра: поймай бабочку!", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 14))
        label.pack(pady=20)
        score_label = tk.Label(content, text="Очки: 0", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 12))
        score_label.pack()
        canvas = tk.Canvas(content, bg="#ffffff", height=220)
        canvas.pack(padx=20, pady=20, fill="x")
        butterfly = canvas.create_text(20, 20, text="🦋", font=("Segoe UI", 16))
        score = {"value": 0}

        def move_butterfly():
            canvas.move(butterfly, 20, 10)
            if canvas.coords(butterfly)[0] > 360:
                canvas.coords(butterfly, 20, 20)
            canvas.after(300, move_butterfly)

        def catch(event):
            score["value"] += 1
            score_label.configure(text=f"Очки: {score['value']}")

        canvas.tag_bind(butterfly, "<Button-1>", catch)
        move_butterfly()

    def open_app_store(self, window):
        content = window.content
        label = tk.Label(content, text="Butterfly App Store", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 14, "bold"))
        label.pack(pady=10)
        listbox = tk.Listbox(content)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)

        packages = []
        if os.path.exists(STORE_DIR):
            for entry in os.listdir(STORE_DIR):
                if entry.endswith(".butterfly"):
                    manifest_path = os.path.join(STORE_DIR, entry, "manifest.json")
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "r", encoding="utf-8") as handle:
                            manifest = json.load(handle)
                            packages.append({"folder": entry, "manifest": manifest})
                            listbox.insert(tk.END, f"{manifest['icon']} {manifest['name']}")

        def install_selected():
            selection = listbox.curselection()
            if not selection:
                return
            package = packages[selection[0]]
            src = os.path.join(STORE_DIR, package["folder"])
            dst = os.path.join(APPS_DIR, package["folder"])
            if os.path.exists(dst):
                messagebox.showinfo("App Store", "Приложение уже установлено")
                return
            shutil.copytree(src, dst)
            installed = load_json(INSTALLED_APPS_FILE, [])
            installed.append({
                "app_id": package["manifest"]["app_id"],
                "name": package["manifest"]["name"],
                "icon": package["manifest"]["icon"],
                "folder": package["folder"]
            })
            save_json(INSTALLED_APPS_FILE, installed)
            self.load_apps()
            self.render_icons()
            messagebox.showinfo("App Store", "Приложение установлено")

        install_button = tk.Button(content, text="Установить", command=install_selected)
        install_button.pack(pady=10)

    def open_installer(self, window):
        content = window.content
        label = tk.Label(content, text="Установщик .butterfly", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 14))
        label.pack(pady=10)

        def pick_package():
            path = filedialog.askdirectory(initialdir=STORE_DIR, title="Выберите .butterfly пакет")
            if not path:
                return
            manifest_path = os.path.join(path, "manifest.json")
            if not os.path.exists(manifest_path):
                messagebox.showerror("Установщик", "manifest.json не найден")
                return
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            dst = os.path.join(APPS_DIR, os.path.basename(path))
            if os.path.exists(dst):
                messagebox.showinfo("Установщик", "Приложение уже установлено")
                return
            shutil.copytree(path, dst)
            installed = load_json(INSTALLED_APPS_FILE, [])
            installed.append({
                "app_id": manifest["app_id"],
                "name": manifest["name"],
                "icon": manifest.get("icon", "🦋"),
                "folder": os.path.basename(path)
            })
            save_json(INSTALLED_APPS_FILE, installed)
            self.load_apps()
            self.render_icons()
            messagebox.showinfo("Установщик", "Приложение установлено")

        pick_button = tk.Button(content, text="Выбрать пакет", command=pick_package)
        pick_button.pack(pady=20)

    def open_settings(self, window):
        content = window.content
        label = tk.Label(content, text="Настройки", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 14, "bold"))
        label.pack(pady=10)

        theme_label = tk.Label(content, text="Тема", bg=self.theme["window"], fg=self.theme["fg"])
        theme_label.pack()
        theme_var = tk.StringVar(value=self.settings["theme"])
        theme_menu = ttk.Combobox(content, textvariable=theme_var, values=list(THEMES.keys()), state="readonly")
        theme_menu.pack(pady=5)

        def apply_theme():
            self.settings["theme"] = theme_var.get()
            save_json(SETTINGS_FILE, self.settings)
            messagebox.showinfo("Настройки", "Перезапустите Butterfly OS для применения темы")

        theme_button = tk.Button(content, text="Применить", command=apply_theme)
        theme_button.pack(pady=5)

        user_label = tk.Label(content, text="Пользователи", bg=self.theme["window"], fg=self.theme["fg"], font=("Segoe UI", 12, "bold"))
        user_label.pack(pady=(20, 5))
        new_user_entry = tk.Entry(content)
        new_user_entry.pack()
        new_password_entry = tk.Entry(content, show="*")
        new_password_entry.pack()

        def add_user():
            username = new_user_entry.get().strip()
            password = new_password_entry.get().strip()
            if not username or not password:
                messagebox.showerror("Пользователь", "Введите имя и пароль")
                return
            users_data = load_json(USERS_FILE, DEFAULT_USERS)
            if any(user["username"] == username for user in users_data["users"]):
                messagebox.showerror("Пользователь", "Такой пользователь уже есть")
                return
            users_data["users"].append({"username": username, "password": password})
            save_json(USERS_FILE, users_data)
            messagebox.showinfo("Пользователь", "Пользователь добавлен")

        add_user_button = tk.Button(content, text="Создать пользователя", command=add_user)
        add_user_button.pack(pady=5)

        def switch_user():
            self.on_logout()

        switch_button = tk.Button(content, text="Сменить пользователя", command=switch_user)
        switch_button.pack(pady=10)

    def open_butterfly_app(self, window, app_id):
        installed = load_json(INSTALLED_APPS_FILE, [])
        package = next((item for item in installed if item["app_id"] == app_id), None)
        if not package:
            messagebox.showerror("Ошибка", "Приложение не найдено")
            return
        package_dir = os.path.join(APPS_DIR, package["folder"])
        app_path = os.path.join(package_dir, "app.py")
        if not os.path.exists(app_path):
            messagebox.showerror("Ошибка", "app.py не найден")
            return
        module_name = f"butterfly_{app_id}"
        spec = None
        if module_name in sys.modules:
            del sys.modules[module_name]
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, app_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run(window.content)


class ButterflyOS:
    def __init__(self, master):
        self.master = master
        master.title("Butterfly OS 13")
        master.state("zoomed")
        master.configure(bg="#000000")
        ensure_directories()
        self.show_boot()

    def show_boot(self):
        BootScreen(self.master, self.show_login)

    def show_login(self):
        if hasattr(self, "desktop"):
            self.desktop.destroy()
        if hasattr(self, "login"):
            self.login.destroy()
        self.login = LoginScreen(self.master, self.on_login)

    def on_login(self, username):
        if hasattr(self, "login"):
            self.login.destroy()
        self.desktop = Desktop(self.master, username, self.show_login)


def main():
    root = tk.Tk()
    app = ButterflyOS(root)
    root.mainloop()


if __name__ == "__main__":
    main()
