import tkinter as tk


def create_rounded_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, theme, width=160, height=34):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=theme["window_bg"])
        self.command = command
        self.theme = theme
        self.rect = create_rounded_rect(
            self,
            2,
            2,
            width - 2,
            height - 2,
            radius=12,
            fill=theme["taskbar_bg"],
            outline=theme["accent"],
        )
        self.label = self.create_text(
            width / 2,
            height / 2,
            text=text,
            fill=theme["text"],
            font=("Segoe UI", 10, "bold"),
        )
        self.bind("<Button-1>", lambda event: self.command())
        self.bind("<Enter>", lambda event: self.itemconfig(self.rect, fill=theme["accent"]))
        self.bind("<Leave>", lambda event: self.itemconfig(self.rect, fill=theme["taskbar_bg"]))

    def update_theme(self, theme):
        self.theme = theme
        self.configure(bg=theme["window_bg"])
        self.itemconfig(self.rect, fill=theme["taskbar_bg"], outline=theme["accent"])
        self.itemconfig(self.label, fill=theme["text"])
