import json
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import importlib.util

APP_NAME = "Butterfly OS 13"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
APPS_DIR = os.path.join(os.path.dirname(__file__), "apps")
FILESYSTEM_DIR = os.path.join(os.path.dirname(__file__), "filesystem")
SAMPLE_APPS_DIR = os.path.join(os.path.dirname(__file__), "sample_apps")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
ICON_POSITIONS_PATH = os.path.join(DATA_DIR, "icon_positions.json")
INSTALLED_APPS_PATH = os.path.join(DATA_DIR, "installed_apps.json")

DEFAULT_SETTINGS = {
    "theme": "light",
    "fullscreen_on_open": True,
    "last_user": None,
}

THEMES = {
    "light": {
        "bg": "#eff3f7",
        "fg": "#1c1c1c",
        "accent": "#1b6ffb",
        "panel": "#ffffff",
        "taskbar": "#d8e2ee",
    },
    "dark": {
        "bg": "#14161a",
        "fg": "#f2f3f7",
        "accent": "#5aa2ff",
        "panel": "#1c1f24",
        "taskbar": "#20242b",
    },
    "neon": {
        "bg": "#0d0f16",
        "fg": "#eaf6ff",
        "accent": "#ff5ad6",
        "panel": "#161a25",
        "taskbar": "#10131d",
    },
}

DEFAULT_USERS = [
    {"username": "admin", "password": "admin"}
]

DEFAULT_DESKTOP_ICONS = [
    {"name": "File Explorer", "app": "file_explorer"},
    {"name": "Settings", "app": "settings"},
    {"name": "Butterfly Notes", "app": "notes"},
    {"name": "Photo Viewer", "app": "photo_viewer"},
    {"name": "Games", "app": "games"},
    {"name": "App Installer", "app": "installer"},
    {"name": "App Store", "app": "app_store"},
]


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(APPS_DIR, exist_ok=True)
    os.makedirs(FILESYSTEM_DIR, exist_ok=True)
    for folder in ("Documents", "Pictures", "Games"):
        os.makedirs(os.path.join(FILESYSTEM_DIR, folder), exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return default


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def init_storage():
    ensure_directories()
    if not os.path.exists(SETTINGS_PATH):
        save_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    if not os.path.exists(USERS_PATH):
        save_json(USERS_PATH, DEFAULT_USERS)
    if not os.path.exists(INSTALLED_APPS_PATH):
        save_json(INSTALLED_APPS_PATH, [])
    if not os.path.exists(ICON_POSITIONS_PATH):
        save_json(ICON_POSITIONS_PATH, {})


def create_sample_apps():
    apps = {
        "butterfly_clock": {
            "display_name": "Butterfly Clock",
            "description": "Минималистичные часы.",
            "entry": "app.py",
            "source": """
import tkinter as tk
import time


def run(app_api):
    root = app_api.new_window("Butterfly Clock")
    label = tk.Label(root, font=("Segoe UI", 36))
    label.pack(expand=True, fill="both")

    def tick():
        label.configure(text=time.strftime("%H:%M:%S"))
        root.after(1000, tick)

    tick()
""",
        },
        "butterfly_todo": {
            "display_name": "Butterfly Todo",
            "description": "Простой список задач.",
            "entry": "app.py",
            "source": """
import tkinter as tk


def run(app_api):
    root = app_api.new_window("Butterfly Todo")
    entry = tk.Entry(root)
    entry.pack(fill="x", padx=12, pady=8)
    listbox = tk.Listbox(root)
    listbox.pack(expand=True, fill="both", padx=12, pady=8)

    def add_task():
        task = entry.get().strip()
        if task:
            listbox.insert("end", task)
            entry.delete(0, "end")

    tk.Button(root, text="Добавить", command=add_task).pack(pady=8)
""",
        },
    }

    for folder, meta in apps.items():
        app_dir = os.path.join(SAMPLE_APPS_DIR, folder)
        os.makedirs(app_dir, exist_ok=True)
        manifest = {
            "name": meta["display_name"],
            "description": meta["description"],
            "entry": meta["entry"],
        }
        with open(os.path.join(app_dir, "manifest.json"), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
        with open(os.path.join(app_dir, "app.py"), "w", encoding="utf-8") as handle:
            handle.write(meta["source"].strip() + "\n")


class AppAPI:
    def __init__(self, os_app):
        self.os_app = os_app

    def new_window(self, title):
        return self.os_app.create_app_window(title)


class WindowFrame(tk.Frame):
    def __init__(self, master, title, on_close, on_minimize, theme):
        super().__init__(master, bg=theme["panel"], highlightbackground=theme["accent"], highlightthickness=1)
        self.title = title
        self.on_close = on_close
        self.on_minimize = on_minimize
        self.theme = theme
        self.build_titlebar()

    def build_titlebar(self):
        titlebar = tk.Frame(self, bg=self.theme["panel"])
        titlebar.pack(fill="x")
        label = tk.Label(titlebar, text=self.title, bg=self.theme["panel"], fg=self.theme["fg"], font=("Segoe UI", 11, "bold"))
        label.pack(side="left", padx=10, pady=6)
        controls = tk.Frame(titlebar, bg=self.theme["panel"])
        controls.pack(side="right")
        tk.Button(controls, text="—", command=self.on_minimize, width=3).pack(side="left")
        tk.Button(controls, text="✕", command=self.on_close, width=3).pack(side="left", padx=(4, 8))


class DesktopIcon(tk.Frame):
    def __init__(self, master, name, command, theme, position=None):
        super().__init__(master, bg=theme["bg"])
        self.command = command
        self.theme = theme
        self.label = tk.Label(self, text=name, bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10))
        self.label.pack(padx=6, pady=4)
        self.bind_events()
        if position:
            self.place(x=position[0], y=position[1])

    def bind_events(self):
        for widget in (self, self.label):
            widget.bind("<Double-Button-1>", lambda _event: self.command())
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)

    def start_drag(self, event):
        self._drag_start = (event.x, event.y)

    def do_drag(self, event):
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.place(x=x, y=y)


class ButterflyOS:
    def __init__(self):
        init_storage()
        create_sample_apps()
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        self.users = load_json(USERS_PATH, DEFAULT_USERS)
        self.installed_apps = load_json(INSTALLED_APPS_PATH, [])
        self.icon_positions = load_json(ICON_POSITIONS_PATH, {})
        self.current_user = None
        self.windows = {}
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1280x720")
        self.root.configure(bg=THEMES[self.settings["theme"]]["bg"])
        self.root.bind("<Control-l>", self.lock_screen)
        self.taskbar_buttons = {}
        self.show_boot_screen()

    def show_boot_screen(self):
        boot = tk.Toplevel(self.root)
        boot.geometry("600x320")
        boot.configure(bg="#0d0f16")
        boot.overrideredirect(True)
        label = tk.Label(boot, text="Butterfly OS 13", fg="#ffffff", bg="#0d0f16", font=("Segoe UI", 24, "bold"))
        label.pack(pady=60)
        progress = ttk.Progressbar(boot, orient="horizontal", length=400, mode="indeterminate")
        progress.pack(pady=20)
        progress.start(10)
        boot.update_idletasks()
        self.root.after(1400, lambda: self.finish_boot(boot))

    def finish_boot(self, boot):
        boot.destroy()
        self.show_login_screen()

    def show_login_screen(self):
        self.clear_root()
        theme = THEMES[self.settings["theme"]]
        self.root.configure(bg=theme["bg"])
        container = tk.Frame(self.root, bg=theme["bg"])
        container.pack(expand=True)
        tk.Label(container, text="Выберите пользователя", font=("Segoe UI", 18, "bold"), bg=theme["bg"], fg=theme["fg"]).pack(pady=12)
        user_var = tk.StringVar(value=self.settings.get("last_user") or self.users[0]["username"])
        user_menu = ttk.Combobox(container, textvariable=user_var, values=[user["username"] for user in self.users], state="readonly")
        user_menu.pack(pady=6)
        password_entry = tk.Entry(container, show="*")
        password_entry.pack(pady=6)

        def attempt_login():
            username = user_var.get()
            password = password_entry.get()
            for user in self.users:
                if user["username"] == username and user["password"] == password:
                    self.current_user = username
                    self.settings["last_user"] = username
                    save_json(SETTINGS_PATH, self.settings)
                    self.show_desktop()
                    return
            messagebox.showerror("Ошибка", "Неверный пароль")

        tk.Button(container, text="Войти", command=attempt_login).pack(pady=8)

    def lock_screen(self, _event=None):
        if not self.current_user:
            return
        self.show_login_screen()

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_desktop(self):
        self.clear_root()
        theme = THEMES[self.settings["theme"]]
        self.desktop = tk.Frame(self.root, bg=theme["bg"])
        self.desktop.pack(expand=True, fill="both")
        self.build_taskbar(theme)
        self.build_start_menu(theme)
        self.build_icons(theme)

    def build_taskbar(self, theme):
        self.taskbar = tk.Frame(self.root, bg=theme["taskbar"], height=48)
        self.taskbar.pack(side="bottom", fill="x")
        start_button = tk.Button(self.taskbar, text="🦋 Start", command=self.toggle_start_menu)
        start_button.pack(side="left", padx=8, pady=6)
        self.taskbar_apps = tk.Frame(self.taskbar, bg=theme["taskbar"])
        self.taskbar_apps.pack(side="left", padx=8)
        self.user_label = tk.Label(self.taskbar, text=f"{self.current_user}", bg=theme["taskbar"], fg=theme["fg"])
        self.user_label.pack(side="right", padx=10)

    def build_start_menu(self, theme):
        self.start_menu = tk.Frame(self.root, bg=theme["panel"], highlightbackground=theme["accent"], highlightthickness=1)
        self.start_menu.place(x=12, y=80, width=260, height=320)
        self.start_menu_visible = False
        tk.Label(self.start_menu, text="Меню Пуск", bg=theme["panel"], fg=theme["fg"], font=("Segoe UI", 12, "bold")).pack(pady=8)
        for item in DEFAULT_DESKTOP_ICONS:
            tk.Button(self.start_menu, text=item["name"], command=lambda app=item["app"]: self.launch_app(app)).pack(fill="x", padx=12, pady=4)
        tk.Button(self.start_menu, text="Переключить пользователя", command=self.switch_user).pack(fill="x", padx=12, pady=4)
        self.start_menu.place_forget()

    def toggle_start_menu(self):
        if self.start_menu_visible:
            self.start_menu.place_forget()
        else:
            self.start_menu.place(x=12, y=80, width=260, height=320)
        self.start_menu_visible = not self.start_menu_visible

    def build_icons(self, theme):
        self.icons = []
        x, y = 40, 40
        for icon in DEFAULT_DESKTOP_ICONS:
            position = self.icon_positions.get(icon["app"]) or (x, y)
            icon_widget = DesktopIcon(self.desktop, icon["name"], command=lambda app=icon["app"]: self.launch_app(app), theme=theme, position=position)
            self.icons.append((icon["app"], icon_widget))
            y += 80
            if y > 480:
                y = 40
                x += 140
        save_button = tk.Button(self.desktop, text="💾 Сохранить позиции", command=self.save_icon_positions)
        save_button.place(relx=1.0, x=-160, y=20)

    def save_icon_positions(self):
        for name, widget in self.icons:
            self.icon_positions[name] = (widget.winfo_x(), widget.winfo_y())
        save_json(ICON_POSITIONS_PATH, self.icon_positions)
        messagebox.showinfo("Готово", "Позиции иконок сохранены.")

    def switch_user(self):
        self.show_login_screen()

    def create_app_window(self, title):
        theme = THEMES[self.settings["theme"]]
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=theme["panel"])
        window.geometry(self.fullscreen_geometry() if self.settings["fullscreen_on_open"] else "920x600")
        frame = WindowFrame(window, title, on_close=lambda: self.close_window(title), on_minimize=lambda: self.minimize_window(title), theme=theme)
        frame.pack(fill="both", expand=True)
        content = tk.Frame(frame, bg=theme["panel"])
        content.pack(fill="both", expand=True)
        window._content = content
        self.windows[title] = window
        self.add_taskbar_button(title)
        return content

    def fullscreen_geometry(self):
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight() - 60
        return f"{width}x{height}+0+0"

    def add_taskbar_button(self, title):
        if title in self.taskbar_buttons:
            return
        theme = THEMES[self.settings["theme"]]
        btn = tk.Button(self.taskbar_apps, text=title, command=lambda: self.restore_window(title), bg=theme["panel"])
        btn.pack(side="left", padx=4)
        self.taskbar_buttons[title] = btn

    def close_window(self, title):
        window = self.windows.pop(title, None)
        if window:
            window.destroy()
        btn = self.taskbar_buttons.pop(title, None)
        if btn:
            btn.destroy()

    def minimize_window(self, title):
        window = self.windows.get(title)
        if window:
            window.withdraw()

    def restore_window(self, title):
        window = self.windows.get(title)
        if window:
            window.deiconify()
            window.lift()

    def launch_app(self, app):
        apps = {
            "file_explorer": self.launch_file_explorer,
            "settings": self.launch_settings,
            "notes": self.launch_notes,
            "photo_viewer": self.launch_photo_viewer,
            "games": self.launch_games,
            "installer": self.launch_installer,
            "app_store": self.launch_app_store,
        }
        if app in apps:
            apps[app]()
        else:
            self.launch_butterfly_app(app)

    def launch_notes(self):
        content = self.create_app_window("Butterfly Notes")
        text = tk.Text(content, wrap="word")
        text.pack(expand=True, fill="both", padx=12, pady=12)

        def save_note():
            path = filedialog.asksaveasfilename(initialdir=FILESYSTEM_DIR, defaultextension=".txt")
            if path:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text.get("1.0", "end"))

        tk.Button(content, text="Сохранить", command=save_note).pack(pady=8)

    def launch_photo_viewer(self):
        content = self.create_app_window("Photo Viewer")
        label = tk.Label(content)
        label.pack(expand=True, fill="both")

        def open_photo():
            path = filedialog.askopenfilename(initialdir=FILESYSTEM_DIR, filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
            if path:
                image = Image.open(path)
                image.thumbnail((900, 600))
                photo = ImageTk.PhotoImage(image)
                label.image = photo
                label.configure(image=photo)

        tk.Button(content, text="Открыть фото", command=open_photo).pack(pady=8)

    def launch_games(self):
        content = self.create_app_window("Games")
        tk.Label(content, text="🎮 Mini Game", font=("Segoe UI", 16)).pack(pady=12)
        score = tk.IntVar(value=0)
        tk.Label(content, textvariable=score, font=("Segoe UI", 24)).pack(pady=8)

        def add_score():
            score.set(score.get() + 1)

        tk.Button(content, text="Нажми меня", command=add_score).pack(pady=12)

    def launch_file_explorer(self):
        content = self.create_app_window("File Explorer")
        current_path = tk.StringVar(value=FILESYSTEM_DIR)
        listbox = tk.Listbox(content)
        listbox.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        scrollbar = tk.Scrollbar(content, command=listbox.yview)
        scrollbar.pack(side="left", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)
        preview = tk.Text(content, width=40)
        preview.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        def refresh():
            listbox.delete(0, "end")
            path = current_path.get()
            for item in os.listdir(path):
                listbox.insert("end", item)

        def open_item(_event=None):
            selection = listbox.curselection()
            if not selection:
                return
            name = listbox.get(selection[0])
            path = os.path.join(current_path.get(), name)
            if os.path.isdir(path):
                current_path.set(path)
                refresh()
                preview.delete("1.0", "end")
            else:
                self.open_file(path, preview)

        def go_up():
            path = os.path.dirname(current_path.get())
            if os.path.commonpath([path, FILESYSTEM_DIR]) == FILESYSTEM_DIR:
                current_path.set(path)
                refresh()

        tk.Button(content, text="⬆️ Вверх", command=go_up).pack(side="bottom", pady=6)
        listbox.bind("<Double-Button-1>", open_item)
        refresh()

    def open_file(self, path, preview_widget):
        preview_widget.delete("1.0", "end")
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            image = Image.open(path)
            image.thumbnail((360, 360))
            photo = ImageTk.PhotoImage(image)
            preview_widget.image = photo
            preview_widget.window_create("end", window=tk.Label(preview_widget, image=photo))
        else:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    preview_widget.insert("end", handle.read())
            except UnicodeDecodeError:
                preview_widget.insert("end", "Невозможно открыть файл.")

    def launch_settings(self):
        content = self.create_app_window("Settings")
        theme_var = tk.StringVar(value=self.settings["theme"])
        fullscreen_var = tk.BooleanVar(value=self.settings["fullscreen_on_open"])
        tk.Label(content, text="Тема:").pack(anchor="w", padx=12, pady=6)
        for theme in THEMES:
            tk.Radiobutton(content, text=theme, variable=theme_var, value=theme).pack(anchor="w", padx=20)
        tk.Checkbutton(content, text="Открывать на весь экран", variable=fullscreen_var).pack(anchor="w", padx=12, pady=6)
        tk.Label(content, text="Создать пользователя:").pack(anchor="w", padx=12, pady=6)
        new_user = tk.Entry(content)
        new_user.pack(anchor="w", padx=12)
        new_pass = tk.Entry(content, show="*")
        new_pass.pack(anchor="w", padx=12, pady=4)

        def save_settings():
            self.settings["theme"] = theme_var.get()
            self.settings["fullscreen_on_open"] = fullscreen_var.get()
            save_json(SETTINGS_PATH, self.settings)
            messagebox.showinfo("Сохранено", "Настройки обновлены. Перезапустите OS.")

        def add_user():
            username = new_user.get().strip()
            password = new_pass.get().strip()
            if not username or not password:
                messagebox.showerror("Ошибка", "Введите имя и пароль")
                return
            if any(user["username"] == username for user in self.users):
                messagebox.showerror("Ошибка", "Пользователь уже существует")
                return
            self.users.append({"username": username, "password": password})
            save_json(USERS_PATH, self.users)
            messagebox.showinfo("Готово", "Пользователь создан")

        tk.Button(content, text="Сохранить настройки", command=save_settings).pack(pady=10)
        tk.Button(content, text="Создать пользователя", command=add_user).pack(pady=6)

    def launch_installer(self):
        content = self.create_app_window("App Installer")
        tk.Label(content, text="Установщик .butterfly", font=("Segoe UI", 14)).pack(pady=10)

        def install():
            path = filedialog.askdirectory(initialdir=os.path.dirname(__file__))
            if not path:
                return
            manifest_path = os.path.join(path, "manifest.json")
            if not os.path.exists(manifest_path):
                messagebox.showerror("Ошибка", "В папке нет manifest.json")
                return
            target = os.path.join(APPS_DIR, os.path.basename(path))
            if os.path.exists(target):
                messagebox.showinfo("Уже установлено", "Приложение уже установлено")
                return
            shutil.copytree(path, target)
            self.installed_apps.append(target)
            save_json(INSTALLED_APPS_PATH, self.installed_apps)
            messagebox.showinfo("Готово", "Приложение установлено")

        tk.Button(content, text="Установить пакет", command=install).pack(pady=8)

    def launch_app_store(self):
        content = self.create_app_window("Butterfly App Store")
        tk.Label(content, text="Butterfly App Store", font=("Segoe UI", 16, "bold")).pack(pady=12)
        store_list = tk.Frame(content)
        store_list.pack(expand=True, fill="both")
        for folder in os.listdir(SAMPLE_APPS_DIR):
            manifest_path = os.path.join(SAMPLE_APPS_DIR, folder, "manifest.json")
            if not os.path.exists(manifest_path):
                continue
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            card = tk.Frame(store_list, relief="ridge", borderwidth=1)
            card.pack(fill="x", padx=12, pady=6)
            tk.Label(card, text=manifest["name"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8, pady=4)
            tk.Label(card, text=manifest["description"]).pack(anchor="w", padx=8)

            def install(folder_name=folder):
                source = os.path.join(SAMPLE_APPS_DIR, folder_name)
                target = os.path.join(APPS_DIR, folder_name)
                if os.path.exists(target):
                    messagebox.showinfo("Установлено", "Уже установлено")
                    return
                shutil.copytree(source, target)
                self.installed_apps.append(target)
                save_json(INSTALLED_APPS_PATH, self.installed_apps)
                messagebox.showinfo("Готово", "Приложение установлено")

            tk.Button(card, text="Установить", command=install).pack(anchor="e", padx=8, pady=6)

    def launch_butterfly_app(self, app_name):
        app_path = os.path.join(APPS_DIR, app_name)
        if not os.path.exists(app_path):
            messagebox.showerror("Ошибка", "Приложение не найдено")
            return
        manifest_path = os.path.join(app_path, "manifest.json")
        if not os.path.exists(manifest_path):
            messagebox.showerror("Ошибка", "Нет manifest.json")
            return
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        entry_path = os.path.join(app_path, manifest.get("entry", "app.py"))
        spec = importlib.util.spec_from_file_location(f"butterfly_{app_name}", entry_path)
        if not spec or not spec.loader:
            messagebox.showerror("Ошибка", "Не удалось загрузить приложение")
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "run"):
            module.run(AppAPI(self))
        else:
            messagebox.showerror("Ошибка", "Нет функции run()")

    def run(self):
        self.root.mainloop()


def main():
    app = ButterflyOS()
    app.run()


if __name__ == "__main__":
    main()
