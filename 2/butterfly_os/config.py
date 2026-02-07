import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
