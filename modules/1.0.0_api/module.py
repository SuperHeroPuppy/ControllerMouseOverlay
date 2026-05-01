import os
import tkinter as tk

from core.app_config import CORE_DIR, CORE_MODULES_DIR, OPTIONAL_MODULES_DIR
from core.controller_constants import COLORS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    left = tk.Frame(frame, bg=COLORS["bg"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right = tk.Frame(frame, bg=COLORS["bg"])
    right.pack(side="left", fill="both", expand=True)

    _build_intro(left)
    _build_paths(self, left)
    _build_lifecycle(left)
    _build_app_access(left)

    _build_info_schema(right)
    _build_module_example(right)
    _build_core_notes(right)
    _build_manager_notes(right)

    return frame


def _build_intro(parent):
    card = _build_card(parent, "Module API", COLORS["panel"])
    tk.Label(
        card,
        text=(
            "Controller Mouse Overlay modules are small Python packages discovered from metadata. "
            "Core modules ship with the app; additional modules live in the project modules folder and can be loaded, unloaded, and reloaded at runtime."
        ),
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=440,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))
    _build_fact_row(card, "Additional folder", "1.0.0_your_module", COLORS["panel"])
    _build_fact_row(card, "Core folder", "1.0.0_your_module_core", COLORS["panel"])
    _build_fact_row(card, "Required files", "info.json and module.py", COLORS["panel"])
    _build_fact_row(card, "Entry point", "build_page(self, parent)", COLORS["panel"])
    _build_fact_row(card, "Live refresh hook", "refresh(self)", COLORS["panel"])


def _build_paths(self, parent):
    card = _build_card(parent, "Module Locations", COLORS["card"])
    _build_path_row(card, "Required core", CORE_DIR, COLORS["card"])
    _build_path_row(card, "Bundled core modules", CORE_MODULES_DIR, COLORS["card"])
    _build_path_row(card, "Additional modules", OPTIONAL_MODULES_DIR, COLORS["card"])
    _build_button(card, "Open Additional Modules Folder", lambda: _open_modules_folder(self), bg=COLORS["panel_alt"])


def _build_lifecycle(parent):
    card = _build_card(parent, "Lifecycle", COLORS["card_alt"])
    for label, value in [
        ("Discovery", "The registry scans module folders and reads info.json without importing module.py."),
        ("Load", "The app imports module.py and calls build_page(self, parent) to create a Tk frame."),
        ("Refresh", "If refresh(self) exists, the app can call it while the module is loaded."),
        ("Unload", "Additional module frames and nav buttons are destroyed; core modules show a missing-module page."),
        ("Reload", "Additional modules are unloaded and imported again from disk."),
    ]:
        _build_wrapped_fact(card, label, value, COLORS["card_alt"])


def _build_app_access(parent):
    card = _build_card(parent, "Useful App Access", COLORS["panel"])
    for label, value in [
        ("self.settings", "Persistent user settings plus runtime flags."),
        ("self.controller_state", "Live analog stick, trigger, and D-pad values."),
        ("self.button_states", "Current pressed state for supported controller inputs."),
        ("self.set_status(text)", "Updates the status badge."),
        ("self.build_utility_button(...)", "Creates a button matching the Utilities module style."),
        ("self.load_optional_module(name)", "Loads and opens an additional module by registry name."),
        ("self.reload_optional_module(name)", "Reloads a loaded additional module from disk."),
    ]:
        _build_wrapped_fact(card, label, value, COLORS["panel"])


def _build_info_schema(parent):
    card = _build_card(parent, "info.json", COLORS["card_alt"])
    _build_code_block(
        card,
        """{
  "version": "1.0.0",
  "display_name": "My Tool",
  "registry_name": "my_tool",
  "description": "What your module does.",
  "creators": ["Your Name"]
}""",
        bg=COLORS["panel_alt"],
    )


def _build_module_example(parent):
    card = _build_card(parent, "module.py", COLORS["panel"])
    _build_code_block(
        card,
        """import tkinter as tk

from core.controller_constants import COLORS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])
    tk.Label(
        frame,
        text="Hello from my module",
        bg=COLORS["bg"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 13),
    ).pack(anchor="w")
    return frame


def refresh(self):
    pass""",
        bg=COLORS["card"],
    )


def _build_core_notes(parent):
    card = _build_card(parent, "Core Module", COLORS["card"])
    for label, value in [
        ("Registry name", "core"),
        ("Folder name", "core"),
        ("Rule", "The required core module is the only module exempt from the versioned folder naming pattern."),
        ("Startup", "The root app.py loader refuses to start if core, core/app.py, or core/info.json is missing."),
        ("Version", "core/info.json holds the program version shown in the Modules page."),
    ]:
        _build_wrapped_fact(card, label, value, COLORS["card"])


def _build_manager_notes(parent):
    card = _build_card(parent, "Modules Page", COLORS["card_alt"])
    for label, value in [
        ("Core modules", "Can be loaded, reloaded, or unloaded unless they are required for management."),
        ("Additional modules", "Can be loaded, opened, reloaded, unloaded, or reloaded together."),
        ("Metadata", "Display name, version, creators, and description come from info.json."),
        ("Errors", "Loader errors are stored on the app and shown by missing-module pages."),
    ]:
        _build_wrapped_fact(card, label, value, COLORS["card_alt"])


def _build_card(parent, title, bg):
    card = tk.Frame(parent, bg=bg, padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    card.pack(fill="x", pady=(0, 14))
    tk.Label(card, text=title, bg=bg, fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    return card


def _build_fact_row(parent, label, value, bg):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=3)
    tk.Label(row, text=label, bg=bg, fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
    tk.Label(row, text=value, bg=bg, fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="right")


def _build_path_row(parent, label, path, bg):
    tk.Label(parent, text=label, bg=bg, fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))
    tk.Label(parent, text=path, bg=bg, fg=COLORS["text"], font=("Consolas", 9), wraplength=420, justify="left").pack(anchor="w", pady=(2, 0))


def _build_wrapped_fact(parent, label, value, bg):
    tk.Label(parent, text=label, bg=bg, fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(10, 0))
    tk.Label(parent, text=value, bg=bg, fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", pady=(2, 0))


def _build_code_block(parent, text, bg):
    code = tk.Text(
        parent,
        height=text.count("\n") + 1,
        bg=bg,
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        bd=0,
        padx=12,
        pady=10,
        font=("Consolas", 9),
        wrap="none",
    )
    code.insert("1.0", text)
    code.configure(state="disabled")
    code.pack(fill="x", pady=(10, 0))


def _build_button(parent, text, command, bg=None):
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
    ).pack(anchor="w", fill="x", pady=(12, 0))


def _open_modules_folder(self):
    os.makedirs(OPTIONAL_MODULES_DIR, exist_ok=True)
    try:
        os.startfile(OPTIONAL_MODULES_DIR)
        self.set_status(f"Opened modules folder at {OPTIONAL_MODULES_DIR}")
    except OSError:
        self.set_status(f"Modules folder is {OPTIONAL_MODULES_DIR}")
