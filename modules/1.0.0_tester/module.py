import tkinter as tk

from core.controller_constants import COLORS, INPUT_LABELS, SUPPORTED_INPUTS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    left = tk.Frame(frame, bg=COLORS["bg"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right = tk.Frame(frame, bg=COLORS["bg"])
    right.pack(side="left", fill="both", expand=True)

    live_card = tk.Frame(left, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    live_card.pack(fill="both", expand=True)

    tk.Label(live_card, text="Live Input Test", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(live_card, text="Press buttons, move sticks, and squeeze triggers to verify incoming controller state.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=480, justify="left").pack(anchor="w", pady=(4, 12))

    self.tester_input_rows = {}
    for input_name in SUPPORTED_INPUTS:
        row = tk.Frame(live_card, bg=COLORS["panel"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=INPUT_LABELS[input_name], bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
        label = tk.Label(row, text="Idle", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10))
        label.pack(side="right")
        self.tester_input_rows[input_name] = label

    axis_card = tk.Frame(right, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    axis_card.pack(fill="both", expand=True)

    tk.Label(axis_card, text="Analog State", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(axis_card, text="These values update live so you can tune deadzone and trigger response.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=360, justify="left").pack(anchor="w", pady=(4, 12))

    self.axis_labels = {}
    for key, label in [
        ("lx", "Left Stick X"),
        ("ly", "Left Stick Y"),
        ("rx", "Right Stick X"),
        ("ry", "Right Stick Y"),
        ("lt", "Left Trigger"),
        ("rt", "Right Trigger"),
        ("dpad_x", "D-Pad X"),
        ("dpad_y", "D-Pad Y"),
    ]:
        row = tk.Frame(axis_card, bg=COLORS["card"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
        value = tk.Label(row, text="0.00", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10))
        value.pack(side="right")
        self.axis_labels[key] = value

    self.tester_status_label = tk.Label(axis_card, text="", bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI", 10), wraplength=360, justify="left")
    self.tester_status_label.pack(anchor="w", pady=(14, 0))

    return frame


def refresh(self):
    for input_name, label in self.tester_input_rows.items():
        active = bool(self.button_states.get(input_name, 0))
        label.config(
            text="Pressed" if active else "Idle",
            fg=COLORS["accent"] if active else COLORS["text"],
        )

    axis_values = {
        "lx": self.controller_state.lx,
        "ly": self.controller_state.ly,
        "rx": self.controller_state.rx,
        "ry": self.controller_state.ry,
        "lt": self.controller_state.lt,
        "rt": self.controller_state.rt,
        "dpad_x": self.controller_state.dpad_x,
        "dpad_y": self.controller_state.dpad_y,
    }
    for key, value in axis_values.items():
        display = f"{value:.2f}" if isinstance(value, float) else str(value)
        self.axis_labels[key].config(text=display)

    self.tester_status_label.config(
        text=(
            f"Selected mapping input: {INPUT_LABELS[self.selected_input]}\n"
            f"Assigned action: {self.describe_action(self.selected_input)}"
        )
    )

