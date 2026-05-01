import tkinter as tk

from core.controller_constants import COLORS, DEFAULT_SETTINGS


SWATCH_PRESETS = [
    "#0b1020", "#11182b", "#161f34", "#243252", "#9babcc", "#edf2ff",
    "#5eead4", "#60a5fa", "#34d399", "#fb7185", "#f59e0b", "#f97316",
    "#ef4444", "#84cc16", "#22d3ee", "#a78bfa", "#ec4899", "#ffffff",
]


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    editor_card = tk.Frame(frame, bg=COLORS["panel_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    editor_card.pack(fill="both", expand=True)
    tk.Label(editor_card, text="Current Style", bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(editor_card, text="Edit colors with live swatches and an inline picker.", bg=COLORS["panel_alt"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    grid = tk.Frame(editor_card, bg=COLORS["panel_alt"])
    grid.pack(fill="both", expand=True)
    for column in range(3):
        grid.grid_columnconfigure(column, weight=1)

    self.style_vars = {}
    self.style_preview_labels = {}
    for index, key in enumerate(DEFAULT_SETTINGS["style"].keys()):
        cell = tk.Frame(grid, bg=COLORS["panel_alt"])
        cell.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 12), pady=(0, 12))
        tk.Label(cell, text=key.replace("_", " ").title(), bg=COLORS["panel_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w")
        var = tk.StringVar(value=self.settings["style"][key])

        row = tk.Frame(cell, bg=COLORS["panel_alt"])
        row.pack(fill="x", pady=(6, 0))

        swatch = tk.Label(
            row,
            text="",
            width=2,
            bg=_preview_color(var.get()),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        swatch.pack(side="left", padx=(0, 8), ipady=5)

        tk.Entry(row, textvariable=var, bg=COLORS["card"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", bd=0, font=("Consolas", 10)).pack(side="left", fill="x", expand=True, ipady=6)

        tk.Button(
            row,
            text="Picker",
            command=lambda style_key=key: _open_picker(self, style_key),
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            bg=COLORS["card_alt"],
            fg=COLORS["text"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        var.trace_add("write", lambda *_args, style_key=key: _update_swatch(self, style_key))
        self.style_vars[key] = var
        self.style_preview_labels[key] = swatch

    picker_card = tk.Frame(editor_card, bg=COLORS["card"], padx=12, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
    self.style_picker_card = picker_card

    top = tk.Frame(picker_card, bg=COLORS["card"])
    top.pack(fill="x")
    self.style_picker_target_label = tk.Label(top, text="", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 11))
    self.style_picker_target_label.pack(side="left")
    tk.Button(
        top,
        text="Close",
        command=lambda: _close_picker(self),
        relief="flat",
        bd=0,
        padx=10,
        pady=6,
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        activebackground=COLORS["card_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI", 9),
        cursor="hand2",
    ).pack(side="right")

    preview_row = tk.Frame(picker_card, bg=COLORS["card"])
    preview_row.pack(fill="x", pady=(10, 0))
    self.style_picker_preview = tk.Label(
        preview_row,
        text="",
        width=12,
        height=4,
        bg=COLORS["panel"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=COLORS["border"],
    )
    self.style_picker_preview.pack(side="left")

    self.style_picker_rgb_label = tk.Label(
        preview_row,
        text="RGB: 0, 0, 0",
        bg=COLORS["card"],
        fg=COLORS["muted"],
        font=("Consolas", 10),
    )
    self.style_picker_rgb_label.pack(side="left", padx=(10, 0), anchor="n")

    self.style_picker_sliders = {}
    self.style_picker_value_labels = {}
    sliders = tk.Frame(picker_card, bg=COLORS["card"])
    sliders.pack(fill="x", pady=(12, 0))

    for idx, (name, value) in enumerate((("R", 0), ("G", 0), ("B", 0))):
        row = tk.Frame(sliders, bg=COLORS["card"])
        row.grid(row=idx, column=0, sticky="ew", pady=(0, 6))
        row.grid_columnconfigure(1, weight=1)

        tk.Label(row, text=name, width=2, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).grid(row=0, column=0, padx=(0, 8))

        slider = tk.Scale(
            row,
            from_=0,
            to=255,
            orient="horizontal",
            showvalue=False,
            command=lambda _val: _on_picker_sliders_changed(self),
            bg=COLORS["card"],
            fg=COLORS["muted"],
            activebackground=COLORS["accent_alt"],
            highlightthickness=0,
            troughcolor=COLORS["panel_alt"],
            relief="flat",
            length=240,
        )
        slider.grid(row=0, column=1, sticky="ew")
        slider.set(value)
        self.style_picker_sliders[name] = slider

        value_label = tk.Label(row, text="0", width=4, bg=COLORS["card"], fg=COLORS["muted"], font=("Consolas", 10))
        value_label.grid(row=0, column=2, padx=(8, 0))
        self.style_picker_value_labels[name] = value_label

    self.style_picker_hex_var = tk.StringVar(value="#000000")
    self.style_picker_hex_var.trace_add("write", lambda *_args: _on_picker_hex_changed(self))
    hex_row = tk.Frame(picker_card, bg=COLORS["card"])
    hex_row.pack(fill="x", pady=(6, 0))
    tk.Label(hex_row, text="HEX", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="left", padx=(0, 8))
    tk.Entry(hex_row, textvariable=self.style_picker_hex_var, bg=COLORS["panel_alt"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", bd=0, font=("Consolas", 10)).pack(side="left", fill="x", expand=True, ipady=5)

    tk.Label(picker_card, text="Quick Swatches", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 6))
    swatch_grid = tk.Frame(picker_card, bg=COLORS["card"])
    swatch_grid.pack(fill="x")
    for i, preset in enumerate(SWATCH_PRESETS):
        tk.Button(
            swatch_grid,
            text="",
            width=3,
            height=1,
            bg=preset,
            activebackground=preset,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            command=lambda value=preset: _set_picker_color(self, value),
            cursor="hand2",
        ).grid(row=i // 9, column=i % 9, padx=3, pady=3)

    actions = tk.Frame(picker_card, bg=COLORS["card"])
    actions.pack(fill="x", pady=(10, 0))
    tk.Button(
        actions,
        text="Use Color",
        command=lambda: _use_picker_color(self),
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
        bg=COLORS["accent_alt"],
        fg=COLORS["text"],
        activebackground=COLORS["accent"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    ).pack(side="right")

    self.style_picker_target_key = None
    self.style_picker_syncing = False
    self.style_picker_open = False

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

    _close_picker(self)

    return frame


def refresh(self):
    for key, var in self.style_vars.items():
        var.set(self.settings["style"][key])
        _update_swatch(self, key)
    if getattr(self, "style_picker_open", False) and self.style_picker_target_key in self.style_vars:
        _set_picker_color(self, self.style_vars[self.style_picker_target_key].get())


def _preview_color(value):
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        hex_body = value[1:]
        if all(ch in "0123456789abcdefABCDEF" for ch in hex_body):
            return value
    return COLORS["panel"]


def _update_swatch(app, style_key):
    preview = getattr(app, "style_preview_labels", {}).get(style_key)
    var = getattr(app, "style_vars", {}).get(style_key)
    if preview is None or var is None:
        return
    if preview.winfo_exists():
        preview.config(bg=_preview_color(var.get()))


def _open_picker(app, style_key):
    if style_key not in getattr(app, "style_vars", {}):
        return

    app.style_picker_open = True
    app.style_picker_target_key = style_key
    app.style_picker_target_label.config(text=f"Picker: {style_key.replace('_', ' ').title()}")
    app.style_picker_card.pack(fill="x", pady=(8, 10))
    _set_picker_color(app, app.style_vars[style_key].get())


def _close_picker(app):
    app.style_picker_open = False
    app.style_picker_target_key = None
    if hasattr(app, "style_picker_target_label"):
        app.style_picker_target_label.config(text="")
    if hasattr(app, "style_picker_card") and app.style_picker_card.winfo_exists():
        app.style_picker_card.pack_forget()


def _set_picker_color(app, value):
    if not hasattr(app, "style_picker_hex_var"):
        return
    safe = _preview_color(value)
    r, g, b = _hex_to_rgb(safe)
    app.style_picker_syncing = True
    app.style_picker_hex_var.set(safe)
    app.style_picker_sliders["R"].set(r)
    app.style_picker_sliders["G"].set(g)
    app.style_picker_sliders["B"].set(b)
    app.style_picker_value_labels["R"].config(text=str(r))
    app.style_picker_value_labels["G"].config(text=str(g))
    app.style_picker_value_labels["B"].config(text=str(b))
    app.style_picker_preview.config(bg=safe)
    app.style_picker_rgb_label.config(text=f"RGB: {r}, {g}, {b}")
    app.style_picker_syncing = False


def _on_picker_sliders_changed(app):
    if getattr(app, "style_picker_syncing", False):
        return
    r = int(float(app.style_picker_sliders["R"].get()))
    g = int(float(app.style_picker_sliders["G"].get()))
    b = int(float(app.style_picker_sliders["B"].get()))
    app.style_picker_value_labels["R"].config(text=str(r))
    app.style_picker_value_labels["G"].config(text=str(g))
    app.style_picker_value_labels["B"].config(text=str(b))
    value = _rgb_to_hex(r, g, b)
    app.style_picker_syncing = True
    app.style_picker_hex_var.set(value)
    app.style_picker_syncing = False
    app.style_picker_preview.config(bg=value)
    app.style_picker_rgb_label.config(text=f"RGB: {r}, {g}, {b}")


def _on_picker_hex_changed(app):
    if getattr(app, "style_picker_syncing", False):
        return
    value = app.style_picker_hex_var.get().strip()
    if not _is_hex_color(value):
        return
    r, g, b = _hex_to_rgb(value)
    app.style_picker_syncing = True
    app.style_picker_sliders["R"].set(r)
    app.style_picker_sliders["G"].set(g)
    app.style_picker_sliders["B"].set(b)
    app.style_picker_syncing = False
    app.style_picker_value_labels["R"].config(text=str(r))
    app.style_picker_value_labels["G"].config(text=str(g))
    app.style_picker_value_labels["B"].config(text=str(b))
    app.style_picker_preview.config(bg=value)
    app.style_picker_rgb_label.config(text=f"RGB: {r}, {g}, {b}")


def _use_picker_color(app):
    target_key = getattr(app, "style_picker_target_key", None)
    if not target_key:
        return
    var = app.style_vars.get(target_key)
    if var is None:
        return
    value = app.style_picker_hex_var.get().strip()
    if _is_hex_color(value):
        var.set(value)


def _is_hex_color(value):
    return isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in value[1:])


def _hex_to_rgb(value):
    safe = _preview_color(value)
    return int(safe[1:3], 16), int(safe[3:5], 16), int(safe[5:7], 16)


def _rgb_to_hex(r, g, b):
    rr = max(0, min(255, int(r)))
    gg = max(0, min(255, int(g)))
    bb = max(0, min(255, int(b)))
    return f"#{rr:02x}{gg:02x}{bb:02x}"
