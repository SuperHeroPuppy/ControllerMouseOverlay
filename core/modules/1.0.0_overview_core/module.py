import tkinter as tk

from core.controller_constants import COLORS, INPUT_LABELS, INPUT_MODE_LABELS, POSITION_LABELS, SUPPORTED_INPUTS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    top_row = tk.Frame(frame, bg=COLORS["bg"])
    top_row.pack(fill="x")

    self.overview_status_frame = tk.Frame(top_row, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    self.overview_status_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

    tk.Label(
        self.overview_status_frame,
        text="Live State",
        bg=COLORS["card"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 13),
    ).pack(anchor="w")

    self.overview_state_labels = {}
    for key, label in [
        ("movement_enabled", "Movement Lock"),
        ("control_windows", "Control Windows"),
        ("auto_enable_movement", "Auto Enable Movement Lock"),
        ("auto_hold_enabled", "Auto Hold"),
        ("dpad_flip_y", "Flip D-Pad Y"),
        ("input_mode", "Movement Lock Input"),
        ("position_mode", "Lock Position"),
        ("custom_slot", "Active Custom Slot"),
    ]:
        row = tk.Frame(self.overview_status_frame, bg=COLORS["card"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
        value = tk.Label(row, text="", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10))
        value.pack(side="right")
        self.overview_state_labels[key] = value

    quick_frame = tk.Frame(top_row, bg=COLORS["card_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    quick_frame.pack(side="left", fill="both", expand=True)

    tk.Label(quick_frame, text="Quick Notes", bg=COLORS["card_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    self.overview_notes = tk.Label(
        quick_frame,
        text="",
        justify="left",
        wraplength=360,
        bg=COLORS["card_alt"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
    )
    self.overview_notes.pack(anchor="w", pady=(10, 0))

    mapping_card = tk.Frame(frame, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    mapping_card.pack(fill="both", expand=True, pady=(14, 0))

    tk.Label(mapping_card, text="Current Controller Mapping", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(mapping_card, text="Every supported controller input can be reassigned from the Mapping page.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    self.mapping_summary_frame = tk.Frame(mapping_card, bg=COLORS["panel"])
    self.mapping_summary_frame.pack(fill="both", expand=True)

    return frame


def refresh(self):
    self.overview_state_labels["movement_enabled"].config(text=self.on_off(self.settings["movement_enabled"]))
    self.overview_state_labels["control_windows"].config(text=self.on_off(self.settings["control_windows"]))
    self.overview_state_labels["auto_enable_movement"].config(text=self.on_off(self.settings["auto_enable_movement"]))
    self.overview_state_labels["auto_hold_enabled"].config(text=self.on_off(self.settings["auto_hold_enabled"]))
    self.overview_state_labels["dpad_flip_y"].config(text=self.on_off(self.settings["dpad_flip_y"]))
    self.overview_state_labels["input_mode"].config(text=INPUT_MODE_LABELS[self.settings["input_mode"]])
    self.overview_state_labels["position_mode"].config(text=POSITION_LABELS[self.settings["position_mode"]])
    self.overview_state_labels["custom_slot"].config(text=POSITION_LABELS[self.settings["custom_slot"]])

    slot = self.settings["custom_slot"]
    custom_pos = self.settings["custom_locations"][slot]
    self.overview_notes.config(
        text=(
            f"Overlay click input: {self.inputs_for_action('ui_click')}\n"
            f"Overlay toggle input: {self.inputs_for_action('toggle_overlay')}\n"
            f"Current custom slot: {POSITION_LABELS[slot]} at X {custom_pos['x']}, Y {custom_pos['y']}"
        )
    )

    for child in self.mapping_summary_frame.winfo_children():
        child.destroy()

    columns = [tk.Frame(self.mapping_summary_frame, bg=COLORS["panel"]) for _ in range(2)]
    for column in columns:
        column.pack(side="left", fill="both", expand=True, padx=(0, 12))

    for index, input_name in enumerate(SUPPORTED_INPUTS):
        parent = columns[index % 2]
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=INPUT_LABELS[input_name], bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
        tk.Label(row, text=self.describe_action(input_name), bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="right")

