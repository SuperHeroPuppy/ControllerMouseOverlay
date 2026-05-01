import tkinter as tk

from core.controller_constants import COLORS, DEFAULT_SETTINGS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    editor_card = tk.Frame(frame, bg=COLORS["panel_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    editor_card.pack(fill="both", expand=True)
    tk.Label(editor_card, text="Current Style", bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(editor_card, text="Edit hex colors and apply them immediately.", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    grid = tk.Frame(editor_card, bg=COLORS["panel_alt"])
    grid.pack(fill="both", expand=True)
    for column in range(3):
        grid.grid_columnconfigure(column, weight=1)

    self.style_vars = {}
    for index, key in enumerate(DEFAULT_SETTINGS["style"].keys()):
        cell = tk.Frame(grid, bg=COLORS["panel_alt"])
        cell.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 12), pady=(0, 12))
        tk.Label(cell, text=key.replace("_", " ").title(), bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        var = tk.StringVar(value=self.settings["style"][key])
        entry = tk.Entry(cell, textvariable=var, bg=COLORS["card"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", bd=0, font=("Consolas", 10))
        entry.pack(fill="x", pady=(6, 0), ipady=6)
        self.style_vars[key] = var

    tk.Button(
        editor_card,
        text="Apply Current Style",
        command=self.apply_style_from_editor,
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
    ).pack(anchor="w", pady=(4, 0))

    return frame


def refresh(self):
    for key, var in self.style_vars.items():
        var.set(self.settings["style"][key])

