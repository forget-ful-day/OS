import json
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk

APP_NAME = "Butterfly OS 13"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "butterfly_data")
FS_DIR = os.path.join(DATA_DIR, "filesystem")
APPS_DIR = os.path.join(DATA_DIR, "apps")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
ICON_POSITIONS = os.path.join(DATA_DIR, "icon_positions.json")

DEFAULT_SETTINGS = {
    "theme": "light",
    "active_user": None,
}

THEMES = {
    "light": {
        "bg": "#e6edf5",
        "fg": "#0b1b2b",
        "accent": "#2b6cb0",
        "panel": "#ffffff",
    },
    "dark": {
        "bg": "#1f2933",
        "fg": "#f5f7fa",
        "accent": "#4fd1c5",
        "panel": "#2d3748",
    },
    "neon": {
        "bg": "#12091a",
        "fg": "#f8f3ff",
        "accent": "#ff77ff",
        "panel": "#1e0f2b",
    },
}


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FS_DIR, exist_ok=True)
    os.makedirs(APPS_DIR, exist_ok=True)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


class WindowManager:
    def __init__(self, desktop):
        self.desktop = desktop
        self.windows = []

    def register(self, window, title):
        self.windows.append(window)
        window.title(title)
        window.protocol("WM_DELETE_WINDOW", lambda: self.close(window))
        window.bind("<FocusIn>", lambda _event: self.focus(window))
        self.desktop.taskbar.add_window(window, title)
        self.focus(window)

    def focus(self, window):
        if window in self.windows:
            window.lift()
        self.desktop.taskbar.highlight(window)

    def close(self, window):
        if window in self.windows:
            self.windows.remove(window)
        self.desktop.taskbar.remove_window(window)
        window.destroy()

    def minimize(self, window):
        window.withdraw()
        self.desktop.taskbar.highlight(None)

    def restore(self, window):
        window.deiconify()
        self.focus(window)


class Taskbar(ttk.Frame):
    def __init__(self, parent, desktop):
        super().__init__(parent)
        self.desktop = desktop
        self.buttons = {}
        self.pack(side=tk.BOTTOM, fill=tk.X)
        self.configure(style="Taskbar.TFrame")
        self.start_button = ttk.Button(self, text="Start", command=self.desktop.toggle_start_menu)
        self.start_button.pack(side=tk.LEFT, padx=4, pady=4)
        self.window_frame = ttk.Frame(self)
        self.window_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def add_window(self, window, title):
        button = ttk.Button(self.window_frame, text=title, command=lambda: self.toggle_window(window))
        button.pack(side=tk.LEFT, padx=4, pady=4)
        self.buttons[window] = button

    def remove_window(self, window):
        button = self.buttons.pop(window, None)
        if button:
            button.destroy()

    def highlight(self, window):
        for win, button in self.buttons.items():
            button.state(["!pressed"])
            if win == window:
                button.state(["pressed"])

    def toggle_window(self, window):
        if window.state() == "withdrawn":
            self.desktop.window_manager.restore(window)
        else:
            self.desktop.window_manager.minimize(window)


class StartMenu(ttk.Frame):
    def __init__(self, parent, desktop):
        super().__init__(parent)
        self.desktop = desktop
        self.configure(style="Panel.TFrame")
        self.apps = []
        ttk.Label(self, text=f"{APP_NAME}", style="Title.TLabel").pack(anchor=tk.W, padx=10, pady=8)
        self.apps_frame = ttk.Frame(self)
        self.apps_frame.pack(fill=tk.BOTH, expand=True, padx=10)

    def set_apps(self, apps):
        for child in self.apps_frame.winfo_children():
            child.destroy()
        for app in apps:
            ttk.Button(
                self.apps_frame,
                text=app["name"],
                command=lambda a=app: self.desktop.launch_app(a),
            ).pack(fill=tk.X, pady=2)


class DesktopIcon(ttk.Frame):
    def __init__(self, parent, desktop, app_info):
        super().__init__(parent)
        self.desktop = desktop
        self.app_info = app_info
        self.label = ttk.Label(self, text=app_info["name"], style="Icon.TLabel")
        self.label.pack(padx=10, pady=4)
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", self.stop_drag)
        self.label.bind("<Double-Button-1>", lambda _event: self.desktop.launch_app(app_info))
        self._drag_data = {"x": 0, "y": 0}

    def start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def drag(self, event):
        x = self.winfo_x() + event.x - self._drag_data["x"]
        y = self.winfo_y() + event.y - self._drag_data["y"]
        self.place(x=x, y=y)

    def stop_drag(self, _event):
        self.desktop.save_icon_positions()


class Desktop:
    def __init__(self, root):
        self.root = root
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.users = load_json(USERS_FILE, {"users": []})
        self.active_user = None
        self.icons = []
        self.window_manager = WindowManager(self)
        self.start_menu = None
        self.lock_overlay = None

        self.root.title(APP_NAME)
        self.root.geometry("1200x720")
        self.root.configure(bg=self.theme()["bg"])
        self.root.bind("<Control-l>", lambda _event: self.lock_screen())

        self.desktop_frame = ttk.Frame(self.root)
        self.desktop_frame.pack(fill=tk.BOTH, expand=True)
        self.desktop_canvas = tk.Canvas(self.desktop_frame, bg=self.theme()["bg"], highlightthickness=0)
        self.desktop_canvas.pack(fill=tk.BOTH, expand=True)

        self.taskbar = Taskbar(self.root, self)
        self.start_menu = StartMenu(self.root, self)
        self.start_menu.place_forget()

        self.apply_theme()
        self.show_boot_screen()
        self.ensure_default_data()
        self.show_login_screen()

    def theme(self):
        return THEMES.get(self.settings.get("theme", "light"), THEMES["light"])

    def apply_theme(self):
        theme = self.theme()
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=theme["bg"])
        style.configure("Panel.TFrame", background=theme["panel"])
        style.configure("Taskbar.TFrame", background=theme["panel"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure("Title.TLabel", background=theme["panel"], foreground=theme["fg"], font=("Segoe UI", 12, "bold"))
        style.configure("Icon.TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure("TButton", background=theme["panel"], foreground=theme["fg"])
        self.root.configure(bg=theme["bg"])
        self.desktop_canvas.configure(bg=theme["bg"])

    def show_boot_screen(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.geometry("400x250+400+200")
        splash.configure(bg="#0d1b2a")
        label = tk.Label(splash, text="Butterfly OS", fg="#8be9fd", bg="#0d1b2a", font=("Segoe UI", 20, "bold"))
        label.pack(expand=True)
        self.root.update()
        for _ in range(10):
            label.config(text=label.cget("text") + " 🦋")
            splash.update()
            time.sleep(0.08)
        splash.destroy()

    def ensure_default_data(self):
        if not self.users["users"]:
            self.users["users"].append({"name": "Admin", "password": "admin"})
            save_json(USERS_FILE, self.users)
        if not os.listdir(APPS_DIR):
            self.install_builtin_apps()

    def install_builtin_apps(self):
        builtins = {
            "Files": self.app_files,
            "Notes": self.app_notes,
            "Photos": self.app_photos,
            "Settings": self.app_settings,
            "App Store": self.app_store,
        }
        for name in builtins:
            app_dir = os.path.join(APPS_DIR, f"{name}.butterfly")
            os.makedirs(app_dir, exist_ok=True)
            manifest = {"name": name, "entry": "main.py"}
            with open(os.path.join(app_dir, "manifest.json"), "w", encoding="utf-8") as handle:
                json.dump(manifest, handle)

    def show_login_screen(self):
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Sign in")
        self.login_window.geometry("400x300+450+200")
        self.login_window.grab_set()
        ttk.Label(self.login_window, text="Select user", style="Title.TLabel").pack(pady=10)
        self.user_list = tk.Listbox(self.login_window)
        for user in self.users["users"]:
            self.user_list.insert(tk.END, user["name"])
        self.user_list.pack(fill=tk.X, padx=20)
        ttk.Label(self.login_window, text="Password").pack(pady=5)
        self.password_entry = ttk.Entry(self.login_window, show="*")
        self.password_entry.pack(fill=tk.X, padx=20)
        ttk.Button(self.login_window, text="Login", command=self.login).pack(pady=10)

    def login(self):
        selection = self.user_list.curselection()
        if not selection:
            messagebox.showwarning("Login", "Pick a user.")
            return
        username = self.user_list.get(selection[0])
        password = self.password_entry.get()
        for user in self.users["users"]:
            if user["name"] == username and user["password"] == password:
                self.active_user = username
                self.settings["active_user"] = username
                save_json(SETTINGS_FILE, self.settings)
                self.login_window.destroy()
                self.render_desktop()
                return
        messagebox.showerror("Login", "Wrong password.")

    def lock_screen(self):
        if self.lock_overlay:
            return
        self.lock_overlay = tk.Toplevel(self.root)
        self.lock_overlay.title("Locked")
        self.lock_overlay.geometry("400x300+450+200")
        self.lock_overlay.grab_set()
        ttk.Label(self.lock_overlay, text=f"Locked: {self.active_user}", style="Title.TLabel").pack(pady=10)
        ttk.Label(self.lock_overlay, text="Password").pack(pady=5)
        password_entry = ttk.Entry(self.lock_overlay, show="*")
        password_entry.pack(fill=tk.X, padx=20)
        ttk.Button(
            self.lock_overlay,
            text="Unlock",
            command=lambda: self.unlock(password_entry.get()),
        ).pack(pady=10)

    def unlock(self, password):
        user = next((u for u in self.users["users"] if u["name"] == self.active_user), None)
        if user and user["password"] == password:
            self.lock_overlay.destroy()
            self.lock_overlay = None
        else:
            messagebox.showerror("Unlock", "Wrong password.")

    def render_desktop(self):
        self.apply_theme()
        self.desktop_canvas.delete("all")
        self.icons = []
        apps = self.list_apps()
        self.start_menu.set_apps(apps)
        positions = load_json(ICON_POSITIONS, {})
        for index, app in enumerate(apps):
            icon = DesktopIcon(self.desktop_canvas, self, app)
            x, y = positions.get(app["name"], (20 + (index * 120) % 600, 20 + (index // 5) * 120))
            icon.place(x=x, y=y)
            self.icons.append(icon)

    def save_icon_positions(self):
        positions = {icon.app_info["name"]: (icon.winfo_x(), icon.winfo_y()) for icon in self.icons}
        save_json(ICON_POSITIONS, positions)

    def list_apps(self):
        apps = []
        for entry in os.listdir(APPS_DIR):
            if entry.endswith(".butterfly"):
                manifest_path = os.path.join(APPS_DIR, entry, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r", encoding="utf-8") as handle:
                        manifest = json.load(handle)
                    apps.append({"name": manifest.get("name", entry), "path": os.path.join(APPS_DIR, entry)})
        return sorted(apps, key=lambda a: a["name"].lower())

    def toggle_start_menu(self):
        if self.start_menu.winfo_ismapped():
            self.start_menu.place_forget()
        else:
            self.start_menu.place(x=10, y=self.root.winfo_height() - 320)
            self.start_menu.lift()

    def launch_app(self, app_info):
        name = app_info["name"]
        if name == "Files":
            self.app_files()
        elif name == "Notes":
            self.app_notes()
        elif name == "Photos":
            self.app_photos()
        elif name == "Settings":
            self.app_settings()
        elif name == "App Store":
            self.app_store()
        else:
            self.launch_package(app_info)

    def launch_package(self, app_info):
        manifest = os.path.join(app_info["path"], "manifest.json")
        if not os.path.exists(manifest):
            messagebox.showerror("App", "Manifest not found")
            return
        with open(manifest, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        entry = data.get("entry")
        if not entry:
            messagebox.showerror("App", "Entry not defined")
            return
        entry_path = os.path.join(app_info["path"], entry)
        if not os.path.exists(entry_path):
            messagebox.showerror("App", "Entry file missing")
            return
        namespace = {"tk": tk, "ttk": ttk, "messagebox": messagebox}
        with open(entry_path, "r", encoding="utf-8") as handle:
            code = handle.read()
        try:
            exec(code, namespace)
            if "run" in namespace:
                namespace["run"](self)
        except Exception as exc:
            messagebox.showerror("App", f"Failed to run app: {exc}")

    def create_window(self, title):
        window = tk.Toplevel(self.root)
        window.geometry("800x500")
        window.attributes("-fullscreen", True)
        header = ttk.Frame(window)
        header.pack(fill=tk.X)
        ttk.Label(header, text=title, style="Title.TLabel").pack(side=tk.LEFT, padx=10)
        ttk.Button(header, text="_", command=lambda: self.window_manager.minimize(window)).pack(side=tk.RIGHT, padx=4)
        ttk.Button(header, text="X", command=lambda: self.window_manager.close(window)).pack(side=tk.RIGHT)
        self.window_manager.register(window, title)
        return window

    def app_files(self):
        window = self.create_window("File Explorer")
        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = ttk.Frame(frame)
        preview.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        preview_label = ttk.Label(preview, text="Select a file")
        preview_label.pack(pady=10)

        def insert_nodes(parent, path):
            for name in os.listdir(path):
                node = tree.insert(parent, tk.END, text=name, values=(os.path.join(path, name),))
                if os.path.isdir(os.path.join(path, name)):
                    tree.insert(node, tk.END)

        def open_node(_event):
            node = tree.focus()
            path = tree.item(node, "values")[0]
            if os.path.isdir(path):
                tree.delete(*tree.get_children(node))
                insert_nodes(node, path)
            else:
                self.open_file(path, preview)

        tree.bind("<<TreeviewOpen>>", open_node)
        tree.bind("<<TreeviewSelect>>", open_node)
        insert_nodes("", FS_DIR)

    def open_file(self, path, preview):
        for child in preview.winfo_children():
            child.destroy()
        ext = os.path.splitext(path)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif"}:
            image = Image.open(path)
            image.thumbnail((400, 400))
            tk_image = ImageTk.PhotoImage(image)
            label = ttk.Label(preview, image=tk_image)
            label.image = tk_image
            label.pack(pady=10)
        else:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except Exception:
                content = "Cannot preview this file."
            text = tk.Text(preview, wrap=tk.WORD)
            text.insert(tk.END, content)
            text.pack(fill=tk.BOTH, expand=True)

    def app_notes(self):
        window = self.create_window("Notes")
        text = tk.Text(window, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        save_button = ttk.Button(window, text="Save", command=lambda: self.save_note(text.get("1.0", tk.END)))
        save_button.pack(pady=6)

    def save_note(self, content):
        note_path = os.path.join(FS_DIR, "note.txt")
        with open(note_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        messagebox.showinfo("Notes", "Saved to filesystem/note.txt")

    def app_photos(self):
        window = self.create_window("Photos")
        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="Open Image", command=lambda: self.open_photo(frame)).pack(pady=10)

    def open_photo(self, frame):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if not path:
            return
        image = Image.open(path)
        image.thumbnail((600, 400))
        tk_image = ImageTk.PhotoImage(image)
        label = ttk.Label(frame, image=tk_image)
        label.image = tk_image
        label.pack(pady=10)

    def app_settings(self):
        window = self.create_window("Settings")
        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(frame, text="Theme").pack(anchor=tk.W)
        theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        for key, label in [("light", "Light"), ("dark", "Dark"), ("neon", "Butterfly Neon")]:
            ttk.Radiobutton(frame, text=label, variable=theme_var, value=key).pack(anchor=tk.W)

        def apply_theme():
            self.settings["theme"] = theme_var.get()
            save_json(SETTINGS_FILE, self.settings)
            self.apply_theme()

        ttk.Button(frame, text="Apply theme", command=apply_theme).pack(pady=10)

        ttk.Label(frame, text="Create user").pack(anchor=tk.W, pady=(20, 0))
        name_entry = ttk.Entry(frame)
        name_entry.pack(fill=tk.X)
        password_entry = ttk.Entry(frame, show="*")
        password_entry.pack(fill=tk.X)

        def create_user():
            name = name_entry.get().strip()
            password = password_entry.get().strip()
            if not name or not password:
                messagebox.showwarning("User", "Enter name and password")
                return
            if any(user["name"] == name for user in self.users["users"]):
                messagebox.showwarning("User", "User already exists")
                return
            self.users["users"].append({"name": name, "password": password})
            save_json(USERS_FILE, self.users)
            messagebox.showinfo("User", "User created")

        ttk.Button(frame, text="Create", command=create_user).pack(pady=6)
        ttk.Button(frame, text="Switch user", command=self.switch_user).pack(pady=6)

    def switch_user(self):
        self.show_login_screen()

    def app_store(self):
        window = self.create_window("Butterfly App Store")
        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(frame, text="Install .butterfly package").pack(anchor=tk.W)
        ttk.Button(frame, text="Install", command=self.install_package).pack(pady=10)
        ttk.Label(frame, text="Installed apps are kept in butterfly_data/apps").pack(anchor=tk.W)

    def install_package(self):
        path = filedialog.askdirectory(title="Select .butterfly package")
        if not path or not path.endswith(".butterfly"):
            messagebox.showwarning("Install", "Select a .butterfly folder")
            return
        dest = os.path.join(APPS_DIR, os.path.basename(path))
        if os.path.exists(dest):
            messagebox.showwarning("Install", "App already installed")
            return
        shutil.copytree(path, dest)
        messagebox.showinfo("Install", "App installed")
        self.render_desktop()


def main():
    ensure_dirs()
    root = tk.Tk()
    Desktop(root)
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
