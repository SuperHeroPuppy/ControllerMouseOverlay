import tkinter as tk

from core.controller_constants import AUTO_HOLD_OPTIONS, COLORS, INPUT_MODE_LABELS, POSITION_LABELS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    left = tk.Frame(frame, bg=COLORS["bg"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right = tk.Frame(frame, bg=COLORS["bg"])
    right.pack(side="left", fill="both", expand=True)

    toggles_card = tk.Frame(left, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    toggles_card.pack(fill="x")

    tk.Label(toggles_card, text="Feature Switches", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(toggles_card, text="These update immediately for the current session.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    for key, label in [
        ("movement_enabled", "Movement Lock Enabled"),
        ("control_windows", "Control Windows"),
        ("auto_enable_movement", "Auto Enable Movement Lock"),
        ("auto_hold_enabled", "Auto Hold Enabled"),
        ("dpad_flip_y", "Flip D-Pad Y"),
    ]:
        row = tk.Frame(toggles_card, bg=COLORS["card"])
        row.pack(fill="x", pady=6)
        label_block = tk.Frame(row, bg=COLORS["card"])
        label_block.pack(side="left", fill="x", expand=True)
        tk.Label(label_block, text=label, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        tk.Label(label_block, text="Click to toggle immediately.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        button = tk.Button(
            row,
            text="",
            command=lambda setting_key=key: self.toggle_setting(setting_key),
            relief="flat",
            bd=0,
            width=10,
            padx=16,
            pady=12,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        )
        button.pack(side="right")
        self.toggle_buttons[key] = button

    sliders_card = tk.Frame(left, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    sliders_card.pack(fill="both", expand=True, pady=(14, 0))

    tk.Label(sliders_card, text="Movement Lock Tuning", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")

    self.deadzone_scale = self.build_slider(sliders_card, "Deadzone", 0.0, 0.9, 0.01, self.on_deadzone_change)
    self.strength_scale = self.build_slider(sliders_card, "Strength", 1, 300, 1, self.on_strength_change)
    self.overlay_speed_scale = self.build_slider(sliders_card, "Overlay Cursor Speed", 5, 120, 1, self.on_overlay_speed_change)
    self.edge_padding_scale = self.build_slider(sliders_card, "Edge Padding", 0, 500, 1, self.on_edge_padding_change)

    selectors_card = tk.Frame(right, bg=COLORS["card_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    selectors_card.pack(fill="both", expand=True)

    tk.Label(selectors_card, text="Modes and Saved Positions", bg=COLORS["card_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(selectors_card, text="Choose how the controller drives movement lock and where the cursor locks.", bg=COLORS["card_alt"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    self.functionality_mode_labels = {}
    self.build_choice_row(selectors_card, "Movement Lock Input", "input_mode", INPUT_MODE_LABELS, self.set_input_mode)
    self.build_choice_row(selectors_card, "Lock Position", "position_mode", POSITION_LABELS, self.set_position_mode)
    self.build_choice_row(
        selectors_card,
        "Active Custom Slot",
        "custom_slot",
        {"custom_1": "Custom 1", "custom_2": "Custom 2", "custom_3": "Custom 3"},
        self.set_custom_slot,
    )
    self.build_choice_row(selectors_card, "Auto Hold Action", "auto_hold_action", AUTO_HOLD_OPTIONS, self.set_auto_hold_action)

    save_row = tk.Frame(selectors_card, bg=COLORS["card_alt"])
    save_row.pack(fill="x", pady=(18, 0))

    self.custom_position_label = tk.Label(save_row, text="", bg=COLORS["card_alt"], fg=COLORS["muted"], font=("Segoe UI", 10))
    self.custom_position_label.pack(side="left")

    tk.Button(
        save_row,
        text="Save Cursor To Slot",
        command=self.capture_custom_location,
        relief="flat",
        bd=0,
        padx=16,
        pady=10,
        bg=COLORS["accent_alt"],
        fg=COLORS["text"],
        activebackground=COLORS["accent_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    ).pack(side="right")

    return frame


def refresh(self):
    for key, button in self.toggle_buttons.items():
        active = bool(self.settings[key])
        button.config(
            text="On" if active else "Off",
            bg=COLORS["success"] if active else COLORS["panel_alt"],
            fg=COLORS["bg"] if active else COLORS["text"],
            activebackground=COLORS["success"] if active else COLORS["panel_alt"],
            activeforeground=COLORS["bg"] if active else COLORS["text"],
        )

    self.functionality_value_labels["Deadzone"].config(text=f"{self.settings['deadzone']:.2f}")
    self.functionality_value_labels["Strength"].config(text=str(self.settings["strength"]))
    self.functionality_value_labels["Overlay Cursor Speed"].config(text=str(self.settings["overlay_cursor_speed"]))
    self.functionality_value_labels["Edge Padding"].config(text=str(self.settings["edge_padding"]))

    self.functionality_mode_labels["input_mode"].config(text=INPUT_MODE_LABELS[self.settings["input_mode"]])
    self.functionality_mode_labels["position_mode"].config(text=POSITION_LABELS[self.settings["position_mode"]])
    self.functionality_mode_labels["custom_slot"].config(text=POSITION_LABELS[self.settings["custom_slot"]])
    self.functionality_mode_labels["auto_hold_action"].config(text=self.settings["auto_hold_action"])

    slot = self.settings["custom_slot"]
    pos = self.settings["custom_locations"][slot]
    self.custom_position_label.config(text=f"{POSITION_LABELS[slot]} saved at X {pos['x']}, Y {pos['y']}")

