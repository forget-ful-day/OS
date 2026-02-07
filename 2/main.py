from butterfly_os import DesktopApp, ensure_directories
from butterfly_os.seed import seed_store


if __name__ == "__main__":
    ensure_directories()
    seed_store()
    app = DesktopApp()
    app.mainloop()
