import tkinter as tk

from core.controller_constants import COLORS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    header = tk.Frame(frame, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    header.pack(fill="x")
    tk.Label(header, text="Module Manager", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(
        header,
        text="Review core and additional modules, including versions, creators, descriptions, and load state.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=860,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    columns = tk.Frame(frame, bg=COLORS["bg"])
    columns.pack(fill="both", expand=True, pady=(14, 0))

    core_card = tk.Frame(columns, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    core_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
    tk.Label(core_card, text="Core Modules", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    self.modules_core_list_frame = tk.Frame(core_card, bg=COLORS["card"])
    self.modules_core_list_frame.pack(fill="both", expand=True, pady=(10, 0))

    optional_card = tk.Frame(columns, bg=COLORS["card_alt"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    optional_card.pack(side="left", fill="both", expand=True)
    optional_header = tk.Frame(optional_card, bg=COLORS["card_alt"])
    optional_header.pack(fill="x")
    tk.Label(optional_header, text="Additional Modules", bg=COLORS["card_alt"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(side="left")
    _build_action_button(optional_header, "Reload All", self.reload_all_optional_modules, bg=COLORS["panel_alt"]).pack_configure(side="right", padx=(0, 0))
    self.modules_optional_list_frame = tk.Frame(optional_card, bg=COLORS["card_alt"])
    self.modules_optional_list_frame.pack(fill="both", expand=True, pady=(10, 0))

    refresh(self)
    return frame


def refresh(self):
    if not hasattr(self, "modules_core_list_frame") or not self.modules_core_list_frame.winfo_exists():
        return
    for child in self.modules_core_list_frame.winfo_children():
        child.destroy()
    for child in self.modules_optional_list_frame.winfo_children():
        child.destroy()

    metadata = self.discover_module_metadata()
    _build_group(self, self.modules_core_list_frame, metadata["core"], "core", COLORS["card"])
    _build_group(self, self.modules_optional_list_frame, metadata["optional"], "optional", COLORS["card_alt"])


def _build_group(self, parent, modules, module_type, bg):
    if not modules:
        tk.Label(
            parent,
            text="No modules found.",
            bg=bg,
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        return

    for module_entry in modules:
        info = module_entry["info"]
        registry_name = info.get("registry_name", module_entry["folder"])
        is_loaded = _is_loaded(self, module_type, registry_name)
        _build_module_row(self, parent, info, module_type, registry_name, is_loaded, bg)


def _build_module_row(self, parent, info, module_type, registry_name, is_loaded, bg):
    row = tk.Frame(parent, bg=COLORS["panel"], padx=12, pady=11, highlightthickness=1, highlightbackground=COLORS["border"])
    row.pack(fill="x", pady=(0, 10))

    title_row = tk.Frame(row, bg=COLORS["panel"])
    title_row.pack(fill="x")
    title = info.get("display_name") or registry_name.replace("_", " ").title()
    tk.Label(title_row, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 11)).pack(side="left")
    tk.Label(
        title_row,
        text="Loaded" if is_loaded else "Unloaded",
        bg=COLORS["accent_alt"] if is_loaded else COLORS["card_alt"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 9),
        padx=8,
        pady=3,
    ).pack(side="right")

    description = info.get("description") or "No description provided."
    tk.Label(
        row,
        text=description,
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=390,
        justify="left",
    ).pack(anchor="w", pady=(8, 0))

    creators = info.get("creators") or []
    if isinstance(creators, list):
        creators_text = ", ".join(str(creator) for creator in creators) or "Unknown"
    else:
        creators_text = str(creators)
    version = info.get("version", "Unknown")
    tk.Label(
        row,
        text=f"Version {version} | Creators: {creators_text}",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=390,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))

    actions = tk.Frame(row, bg=COLORS["panel"])
    actions.pack(fill="x", pady=(10, 0))
    if module_type == "core":
        if is_loaded:
            if registry_name == "core":
                _build_action_button(actions, "Reload", lambda: self.set_status("Core reload requires restarting the app"), disabled=True)
                _build_action_button(actions, "Unload", lambda: self.set_status("Core is required and cannot be unloaded"), disabled=True)
            elif registry_name == "modules":
                _build_action_button(actions, "Reload", lambda name=registry_name: self.load_core_module(name, activate=False))
                _build_action_button(actions, "Unload", lambda: self.set_status("Modules page stays loaded so modules can be managed"), disabled=True)
            else:
                _build_action_button(actions, "Reload", lambda name=registry_name: self.load_core_module(name, activate=False))
                _build_action_button(actions, "Unload", lambda name=registry_name: self.unload_core_module(name), bg=COLORS["danger"])
        else:
            _build_action_button(actions, "Load", lambda name=registry_name: self.load_core_module(name, activate=False), bg=COLORS["accent_alt"])
    else:
        if is_loaded:
            _build_action_button(actions, "Open", lambda name=registry_name: self.set_active_page(name))
            _build_action_button(actions, "Reload", lambda name=registry_name: self.reload_optional_module(name))
            _build_action_button(actions, "Unload", lambda name=registry_name: self.unload_optional_module(name), bg=COLORS["danger"])
        else:
            _build_action_button(actions, "Load", lambda name=registry_name: self.load_optional_module(name), bg=COLORS["accent_alt"])


def _is_loaded(self, module_type, registry_name):
    if module_type == "core":
        if registry_name == "core":
            return True
        return self.core_modules.get(registry_name) is not None
    return registry_name in self.loaded_optional_modules


def _build_action_button(parent, text, command, bg=None, disabled=False):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
        bg=COLORS["card"] if bg is None else bg,
        fg=COLORS["muted"] if disabled else COLORS["text"],
        activebackground=COLORS["card_alt"] if bg is None else bg,
        activeforeground=COLORS["text"],
        disabledforeground=COLORS["muted"],
        font=("Segoe UI Semibold", 9),
        cursor="arrow" if disabled else "hand2",
        state="disabled" if disabled else "normal",
    )
    button.pack(side="left", padx=(0, 8))
    return button
