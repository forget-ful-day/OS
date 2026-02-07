# Butterfly OS 13 (Python Prototype)

This is a Tkinter-based prototype that mimics a Windows-like desktop called **Butterfly OS 13**.

## Features
- Desktop with draggable icons (positions saved).
- Start menu with File Explorer, Settings, App Store, Control Center, Lock, Switch User.
- Taskbar with running app buttons.
- User management with password-based login and lock screen.
- Themes: Light, Dark, Butterfly Neon.
- File Explorer with upload, folders, and text/image viewers.
- `.butterfly` app packages with manifest + Python code.
- Simple App Store that installs `.butterfly` apps.
- Rounded buttons and colorful emoji icons.
- Control Center includes 25 quick feature toggles.

## Run
```bash
python main.py
```

Default user: `admin` / `admin`.

## Data layout
- `butterfly_fs/` – simulated file system for File Explorer.
- `apps_installed/` – installed `.butterfly` apps.
- `store/` – available `.butterfly` apps for App Store.
- `data/` – settings and user accounts.
