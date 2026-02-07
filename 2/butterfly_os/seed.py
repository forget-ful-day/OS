import json
import os

from .config import STORE_DIR


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
