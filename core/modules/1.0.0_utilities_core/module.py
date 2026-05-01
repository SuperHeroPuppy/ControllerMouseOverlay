import tkinter as tk

from core.app_config import EXPORT_DIR
from core.controller_constants import COLORS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    left = tk.Frame(frame, bg=COLORS["bg"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right = tk.Frame(frame, bg=COLORS["bg"])
    right.pack(side="left", fill="both", expand=True)

    settings_card = tk.Frame(left, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    settings_card.pack(fill="x")
    tk.Label(settings_card, text="Settings", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(settings_card, text="Import or export saved settings, or clear local app data.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))

    self.build_utility_button(settings_card, "Export Settings", self.export_settings)
    self.build_utility_button(settings_card, "Import Settings", self.import_settings)
    self.build_utility_button(settings_card, "Clear Data", self.clear_data, bg=COLORS["danger"])

    style_card = tk.Frame(left, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    style_card.pack(fill="x", pady=(14, 0))
    tk.Label(style_card, text="Styles", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(style_card, text="Import a style file or export the active/default style JSON.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))

    self.build_utility_button(style_card, "Export Current Style", self.export_current_style, bg=COLORS["panel_alt"])
    self.build_utility_button(style_card, "Export Default Style", self.export_default_style, bg=COLORS["panel_alt"])
    self.build_utility_button(style_card, "Import Style", self.import_style, bg=COLORS["panel_alt"])

    sheet_card = tk.Frame(right, bg=COLORS["card_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    sheet_card.pack(fill="x")
    tk.Label(sheet_card, text="Control Sheets", bg=COLORS["card_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(sheet_card, text="Move mappings, movement lock mode, and saved positions between setups.", bg=COLORS["card_alt"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))

    self.build_utility_button(sheet_card, "Export Control Sheet", self.export_control_sheet, bg=COLORS["panel_alt"])
    self.build_utility_button(sheet_card, "Import Control Sheet", self.import_control_sheet, bg=COLORS["panel_alt"])

    location_card = tk.Frame(right, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    location_card.pack(fill="x", pady=(14, 0))
    tk.Label(location_card, text="Export Location", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(location_card, text=EXPORT_DIR, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))

    self.build_utility_button(location_card, "Open Export Folder", self.open_export_folder, bg=COLORS["accent_alt"])

    exit_card = tk.Frame(right, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    exit_card.pack(fill="x", pady=(14, 0))
    tk.Label(exit_card, text="Application", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(exit_card, text="Close the overlay and stop controller handling.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(4, 12))

    self.build_utility_button(exit_card, "Exit Controller Mouse Overlay", self.stop, bg=COLORS["danger"])

    return frame


def build_button(self, parent, text, command, bg=None):
    tk.Button(
        parent,
        text=text,
        command=command,
        relief="flat",
        bd=0,
        padx=12,
        pady=9,
        bg=bg or COLORS["card"],
        fg=COLORS["text"],
        activebackground=bg or COLORS["card_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    ).pack(anchor="w", fill="x", pady=(0, 8))

