import json
import os
import shutil
import sys
import time
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
        self.geometry("760x520")
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

    def close(self):
        if self.on_close:
            self.on_close()
        self.destroy()


class FileExplorer(Window):
    def __init__(self, master, theme, path):
        super().__init__(master, "File Explorer", theme)
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
        tk.Button(buttons, text="Upload", command=self.upload_file).pack(fill="x", pady=4)
        tk.Button(buttons, text="New Folder", command=self.create_folder).pack(fill="x", pady=4)
        tk.Button(buttons, text="Open", command=self.open_item).pack(fill="x", pady=4)
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
        messagebox.showinfo("Butterfly OS", f"File: {name}\nPath: {full_path}")

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        shutil.copy(file_path, self.path)
        self.refresh()

    def create_folder(self):
        folder_name = tk.simpledialog.askstring("New Folder", "Folder name:")
        if not folder_name:
            return
        os.makedirs(os.path.join(self.path, folder_name), exist_ok=True)
        self.refresh()


class TextViewer(Window):
    def __init__(self, master, theme, file_path):
        super().__init__(master, f"Text - {os.path.basename(file_path)}", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        text = tk.Text(body, wrap="word")
        text.pack(fill="both", expand=True)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            text.insert("1.0", file.read())


class ImageViewer(Window):
    def __init__(self, master, theme, file_path):
        super().__init__(master, f"Image - {os.path.basename(file_path)}", theme)
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        try:
            self.photo = tk.PhotoImage(file=file_path)
            label = tk.Label(body, image=self.photo, bg=theme["window_bg"])
            label.pack(expand=True)
        except tk.TclError:
            tk.Label(
                body,
                text="Image format not supported by Tk.",
                bg=theme["window_bg"],
                fg=theme["text"],
            ).pack(expand=True)


class AppInstaller(Window):
    def __init__(self, master, theme, on_install):
        super().__init__(master, "Butterfly App Store", theme)
        self.on_install = on_install
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(body)
        self.listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        for entry in sorted(os.listdir(STORE_DIR)):
            if entry.endswith(".butterfly"):
                self.listbox.insert(tk.END, entry)
        tk.Button(body, text="Install", command=self.install_selected).pack(side="right", padx=10)

    def install_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        name = self.listbox.get(selection[0])
        src = os.path.join(STORE_DIR, name)
        dst = os.path.join(APPS_DIR, name)
        if os.path.exists(dst):
            messagebox.showinfo("Butterfly OS", "Already installed.")
            return
        shutil.copytree(src, dst)
        self.on_install()
        messagebox.showinfo("Butterfly OS", f"Installed {name}.")


class SettingsWindow(Window):
    def __init__(self, master, theme, config, users, on_update):
        super().__init__(master, "Settings", theme)
        self.config = config
        self.users = users
        self.on_update = on_update
        body = tk.Frame(self, bg=theme["window_bg"])
        body.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(body, text="Theme", bg=theme["window_bg"], fg=theme["text"]).pack(anchor="w")
        self.theme_var = tk.StringVar(value=config.get("theme", "light"))
        for key in THEMES:
            tk.Radiobutton(
                body,
                text=key.title(),
                variable=self.theme_var,
                value=key,
                bg=theme["window_bg"],
                fg=theme["text"],
                selectcolor=theme["window_bg"],
            ).pack(anchor="w")
        tk.Button(body, text="Apply Theme", command=self.apply_theme).pack(pady=6)
        tk.Label(body, text="Users", bg=theme["window_bg"], fg=theme["text"]).pack(anchor="w", pady=(12, 0))
        self.user_list = tk.Listbox(body, height=4)
        self.user_list.pack(fill="x")
        for name in self.users["users"]:
            self.user_list.insert(tk.END, name)
        tk.Button(body, text="Add User", command=self.add_user).pack(pady=4)

    def apply_theme(self):
        self.config["theme"] = self.theme_var.get()
        self.on_update()

    def add_user(self):
        username = tk.simpledialog.askstring("New User", "Username:")
        if not username:
            return
        if username in self.users["users"]:
            messagebox.showerror("Butterfly OS", "User already exists.")
            return
        password = tk.simpledialog.askstring("New User", "Password:", show="*")
        if not password:
            return
        self.users["users"][username] = {"password": password}
        save_json(USERS_PATH, self.users)
        self.user_list.insert(tk.END, username)
        messagebox.showinfo("Butterfly OS", "User created.")


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
            text="Welcome to Butterfly OS",
            font=("Segoe UI", 20, "bold"),
            bg=theme["desktop_bg"],
            fg=theme["accent"],
        ).pack(pady=10)
        tk.Label(frame, text="Select user", bg=theme["desktop_bg"], fg=theme["text"]).pack()
        self.user_var = tk.StringVar(value=list(users["users"].keys())[0])
        user_menu = ttk.Combobox(frame, textvariable=self.user_var, values=list(users["users"].keys()))
        user_menu.pack(pady=4)
        tk.Label(frame, text="Password", bg=theme["desktop_bg"], fg=theme["text"]).pack()
        self.pass_entry = tk.Entry(frame, show="*")
        self.pass_entry.pack(pady=4)
        tk.Button(frame, text="Login", command=self.login).pack(pady=8)

    def login(self):
        user = self.user_var.get()
        password = self.pass_entry.get()
        if self.users["users"].get(user, {}).get("password") == password:
            self.on_login(user)
            self.destroy()
        else:
            messagebox.showerror("Butterfly OS", "Invalid password.")


class DesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_directories()
        self.config_data = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.users = load_json(USERS_PATH, DEFAULT_USERS)
        self.theme = THEMES[self.config_data.get("theme", "light")]
        self.title("Butterfly OS 13")
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.state("zoomed")
        self.configure(bg=self.theme["desktop_bg"])
        self.desktop = tk.Canvas(self, bg=self.theme["desktop_bg"], highlightthickness=0)
        self.desktop.pack(fill="both", expand=True)
        self.taskbar = tk.Frame(self, bg=self.theme["taskbar_bg"], height=40)
        self.taskbar.place(relx=0, rely=1, anchor="sw", relwidth=1)
        self.start_button = tk.Button(
            self.taskbar,
            text="Start",
            command=self.toggle_start_menu,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
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
            ("File Explorer", lambda: self.launch_app("explorer")),
            ("Settings", lambda: self.launch_app("settings")),
            ("App Store", lambda: self.launch_app("store")),
            ("Switch User", self.show_login),
            ("Lock", self.lock_screen),
            ("Shutdown", self.quit),
        ]
        for label, command in buttons:
            tk.Button(
                self.start_menu,
                text=label,
                command=command,
                bg=self.theme["window_bg"],
                fg=self.theme["text"],
                relief="flat",
            ).pack(fill="x", padx=8, pady=4)

    def _build_icons(self):
        self.icons = {
            "File Explorer": {"app": "explorer"},
            "Settings": {"app": "settings"},
            "App Store": {"app": "store"},
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
            icon = self.desktop.create_rectangle(
                x - 28,
                y - 28,
                x + 28,
                y + 28,
                fill=self.theme["window_bg"],
                outline=self.theme["accent"],
                tags=("icon", name),
            )
            text = self.desktop.create_text(
                x,
                y + 40,
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
            self.launch_icon(event)
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
            tk.Button(
                self.taskbar_apps,
                text=name,
                command=lambda n=name: self.focus_window(n),
                bg=self.theme["taskbar_bg"],
                fg=self.theme["text"],
                relief="flat",
            ).pack(side="left", padx=4)

    def focus_window(self, name):
        window = self.open_windows.get(name)
        if window and window.winfo_exists():
            window.deiconify()
            window.lift()

    def launch_app(self, app_name):
        if app_name == "explorer":
            self._open_window("File Explorer", lambda: FileExplorer(self, self.theme, FS_DIR))
            return
        if app_name == "settings":
            self._open_window(
                "Settings",
                lambda: SettingsWindow(self, self.theme, self.config_data, self.users, self.reload_theme),
            )
            return
        if app_name == "store":
            self._open_window("App Store", lambda: AppInstaller(self, self.theme, self.refresh_apps))
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
            messagebox.showerror("Butterfly OS", "Invalid Butterfly app.")
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
                text=f"App error: {exc}",
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
        self.start_button.configure(bg=self.theme["accent"])
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
            text="Locked",
            font=("Segoe UI", 20, "bold"),
            bg=self.theme["desktop_bg"],
            fg=self.theme["accent"],
        ).pack(pady=10)
        tk.Label(frame, text="Password", bg=self.theme["desktop_bg"], fg=self.theme["text"]).pack()
        entry = tk.Entry(frame, show="*")
        entry.pack(pady=6)

        def unlock():
            user = self.config_data.get("last_user", "admin")
            if self.users["users"].get(user, {}).get("password") == entry.get():
                lock.destroy()
            else:
                messagebox.showerror("Butterfly OS", "Invalid password.")

        tk.Button(frame, text="Unlock", command=unlock).pack(pady=8)


def seed_store():
    demo_app = os.path.join(STORE_DIR, "Notes.butterfly")
    if not os.path.exists(demo_app):
        os.makedirs(demo_app, exist_ok=True)
        with open(os.path.join(demo_app, "manifest.json"), "w", encoding="utf-8") as file:
            json.dump({"name": "Notes"}, file, indent=2)
        with open(os.path.join(demo_app, "main.py"), "w", encoding="utf-8") as file:
            file.write(
                """
import tkinter as tk

tk.Label(frame, text='Butterfly Notes', font=('Segoe UI', 14, 'bold'), bg=theme['window_bg'], fg=theme['text']).pack(pady=10)
text = tk.Text(frame)
text.pack(fill='both', expand=True, padx=10, pady=10)
"""
            )


if __name__ == "__main__":
    ensure_directories()
    seed_store()
    app = DesktopApp()
    app.mainloop()
