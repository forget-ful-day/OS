import tkinter as tk
from tkinter import ttk, messagebox


class AntivirusSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AuroraShield Antivirus — Simulator")
        self.geometry("820x540")
        self.resizable(False, False)

        self.is_scanning = False
        self.first_scan = True
        self.scan_progress = tk.IntVar(value=0)

        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")

        title = ttk.Label(
            header,
            text="AuroraShield Antivirus",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(side="left")

        subtitle = ttk.Label(
            header,
            text="(Simulation Only)",
            foreground="#5e6d7a",
            font=("Segoe UI", 10, "italic"),
        )
        subtitle.pack(side="left", padx=(8, 0))

        self.status_label = ttk.Label(
            header,
            text="Ready to scan",
            foreground="#2b7a2b",
            font=("Segoe UI", 11),
        )
        self.status_label.pack(side="right")

        content = ttk.Frame(self, padding=(12, 0, 12, 12))
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content)
        left.pack(side="left", fill="y")

        right = ttk.Frame(content)
        right.pack(side="right", fill="both", expand=True)

        scan_card = ttk.LabelFrame(left, text="Quick Scan", padding=12)
        scan_card.pack(fill="x", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(
            scan_card,
            orient="horizontal",
            mode="determinate",
            length=250,
            maximum=100,
            variable=self.scan_progress,
        )
        self.progress_bar.pack(fill="x")

        self.progress_label = ttk.Label(scan_card, text="0%")
        self.progress_label.pack(pady=(6, 12))

        self.scan_button = ttk.Button(
            scan_card,
            text="Start Scan",
            command=self.start_scan,
        )
        self.scan_button.pack(fill="x")

        info_card = ttk.LabelFrame(left, text="Protection Status", padding=12)
        info_card.pack(fill="x")

        ttk.Label(info_card, text="Real-time shield: ACTIVE").pack(anchor="w")
        ttk.Label(info_card, text="Firewall: ACTIVE").pack(anchor="w")
        ttk.Label(info_card, text="Last scan: Never").pack(anchor="w", pady=(0, 6))
        ttk.Label(
            info_card,
            text="This app is a harmless UI demo.\nNo files are scanned or modified.",
            foreground="#5e6d7a",
        ).pack(anchor="w")

        logs = ttk.LabelFrame(right, text="Scan Intelligence", padding=12)
        logs.pack(fill="both", expand=True)

        log_frames = ttk.Frame(logs)
        log_frames.pack(fill="both", expand=True)

        left_log = ttk.LabelFrame(log_frames, text="Scan Log", padding=8)
        left_log.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right_log = ttk.LabelFrame(log_frames, text="System Console", padding=8)
        right_log.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self.scan_log = tk.Text(left_log, height=18, wrap="word")
        self.scan_log.pack(fill="both", expand=True)

        self.system_log = tk.Text(right_log, height=18, wrap="word")
        self.system_log.pack(fill="both", expand=True)

        self._log(self.scan_log, "Welcome to AuroraShield simulation.")
        self._log(self.system_log, "Console ready.")

    def _log(self, widget: tk.Text, message: str):
        widget.insert("end", f"{message}\n")
        widget.see("end")

    def start_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.scan_button.configure(state="disabled")
        self.status_label.configure(text="Scanning...", foreground="#c07a00")
        self._log(self.scan_log, "Initializing scan engines...")

        if self.first_scan:
            self._simulate_glitchy_scan()
        else:
            self._simulate_normal_scan()

    def _simulate_glitchy_scan(self):
        self._log(self.system_log, "Diagnostic ping: writing to wrong console.")
        self._log(self.system_log, "Notice: progress offset detected.")
        self._run_progress_sequence(-20, 100, 4)

    def _simulate_normal_scan(self):
        self._run_progress_sequence(0, 100, 6)

    def _run_progress_sequence(self, start_value: int, end_value: int, step_delay: int):
        values = list(range(start_value, end_value + 1))

        def step(index=0):
            if index >= len(values):
                self._finish_scan()
                return
            value = values[index]
            display_value = value
            self.progress_label.configure(text=f"{display_value}%")
            self.scan_progress.set(max(0, min(100, value)))
            if value < 0:
                self._log(self.system_log, f"Progress drift: {value}%")
            elif value in (0, 25, 50, 75, 100):
                self._log(self.scan_log, f"Scanning sectors... {value}%")
            self.after(step_delay * 20, lambda: step(index + 1))

        step()

    def _finish_scan(self):
        self.is_scanning = False
        self.scan_button.configure(state="normal")
        self.status_label.configure(text="Scan complete", foreground="#2b7a2b")
        self._log(self.scan_log, "No threats found. Simulation complete.")
        self.progress_label.configure(text="100%")
        if self.first_scan:
            self.first_scan = False
            self._open_quest_window()

    def _open_quest_window(self):
        quest = QuestWindow(self)
        quest.grab_set()


class QuestWindow(tk.Toplevel):
    def __init__(self, master: AntivirusSimulator):
        super().__init__(master)
        self.title("Quarantine Challenge")
        self.geometry("520x520")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._block_close)

        self.step = 0
        self.steps = [
            ("Step 1: Type 'AURORA' to confirm.", self._check_phrase),
            ("Step 2: 7 + 5 = ?", self._check_math),
            ("Step 3: Select the blue shield.", self._check_choice),
            ("Step 4: Type the word 'SAFE'.", self._check_phrase_safe),
            ("Step 5: What day comes after Monday?", self._check_day),
            ("Step 6: Click the checkbox to finish.", self._check_checkbox),
        ]

        self.message = ttk.Label(
            self,
            text="Scan complete. To exit the simulation, complete 6 quick steps.",
            wraplength=480,
            font=("Segoe UI", 10),
        )
        self.message.pack(pady=16)

        self.step_label = ttk.Label(
            self,
            text="",
            font=("Segoe UI", 11, "bold"),
        )
        self.step_label.pack(pady=8)

        self.entry = ttk.Entry(self)
        self.entry.pack(pady=6, fill="x", padx=40)

        self.choice_var = tk.StringVar(value="red")
        choices = ttk.Frame(self)
        choices.pack(pady=6)
        ttk.Radiobutton(choices, text="Red shield", value="red", variable=self.choice_var).pack(
            side="left", padx=10
        )
        ttk.Radiobutton(
            choices, text="Blue shield", value="blue", variable=self.choice_var
        ).pack(side="left", padx=10)

        self.checkbox_var = tk.BooleanVar(value=False)
        self.checkbox = ttk.Checkbutton(
            self, text="I confirm the simulation can close.", variable=self.checkbox_var
        )
        self.checkbox.pack(pady=6)

        self.feedback = ttk.Label(self, text="", foreground="#c0392b")
        self.feedback.pack(pady=6)

        self.next_button = ttk.Button(self, text="Verify", command=self._handle_step)
        self.next_button.pack(pady=12)

        self._update_step()

    def _block_close(self):
        messagebox.showinfo(
            "Simulation",
            "Please complete the 6-step challenge to close this demo window.",
        )

    def _update_step(self):
        prompt, _ = self.steps[self.step]
        self.step_label.configure(text=prompt)
        self.entry.delete(0, "end")
        self.feedback.configure(text="")

    def _handle_step(self):
        _, validator = self.steps[self.step]
        if validator():
            self.step += 1
            if self.step >= len(self.steps):
                messagebox.showinfo("Simulation", "Challenge complete. You may close the app.")
                self.destroy()
                return
            self._update_step()

    def _check_phrase(self):
        return self._check_entry("AURORA")

    def _check_math(self):
        return self._check_entry("12")

    def _check_choice(self):
        if self.choice_var.get() == "blue":
            self.feedback.configure(text="")
            return True
        self.feedback.configure(text="Hint: choose the blue shield.")
        return False

    def _check_phrase_safe(self):
        return self._check_entry("SAFE")

    def _check_day(self):
        value = self.entry.get().strip().lower()
        if value == "tuesday":
            self.feedback.configure(text="")
            return True
        self.feedback.configure(text="Hint: It's Tuesday.")
        return False

    def _check_checkbox(self):
        if self.checkbox_var.get():
            self.feedback.configure(text="")
            return True
        self.feedback.configure(text="Check the confirmation box to finish.")
        return False

    def _check_entry(self, expected: str):
        value = self.entry.get().strip().upper()
        if value == expected:
            self.feedback.configure(text="")
            return True
        self.feedback.configure(text=f"Enter {expected} to continue.")
        return False


if __name__ == "__main__":
    app = AntivirusSimulator()
    app.mainloop()
