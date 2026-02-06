import tkinter as tk


def run(container):
    container.configure(bg="#1d0044")
    label = tk.Label(container, text="Butterfly Clock", fg="#ff6ec7", bg="#1d0044", font=("Segoe UI", 16, "bold"))
    label.pack(pady=20)
    time_label = tk.Label(container, text="", fg="#f7e6ff", bg="#1d0044", font=("Segoe UI", 28))
    time_label.pack(pady=10)

    def update():
        now = container.winfo_toplevel().tk.call("clock", "format", container.winfo_toplevel().tk.call("clock", "seconds"), "-format", "%H:%M:%S")
        time_label.configure(text=now)
        container.after(1000, update)

    update()
