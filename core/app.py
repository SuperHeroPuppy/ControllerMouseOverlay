import ctypes
import json
import os
import threading
import time
import tkinter as tk
from copy import deepcopy
from tkinter import filedialog, ttk

from inputs import get_gamepad
import win32api
import win32con

from core.app_config import APP_DIR, COMMUNITY_MODULES_DIR, CONTROL_SHEET_EXPORT_DIR, CORE_DIR, CORE_MODULES_DIR, EXPORT_DIR, OPTIONAL_MODULES_DIR, SETTINGS_PATH, STYLE_EXPORT_DIR
from core.controller_constants import (
    ACTION_DEFINITIONS,
    ACTION_KEYS,
    AUTO_HOLD_OPTIONS,
    COLORS,
    DEFAULT_SETTINGS,
    INPUT_LABELS,
    INPUT_MODE_LABELS,
    POSITION_LABELS,
    SUPPORTED_INPUTS,
    WINDOWS_REMAP_OPTIONS,
)
from core.controller_state import ControllerState, clamp
from core.module_registry import ModuleLoadError, discover_registered_modules, load_registered_module, read_module_info


CORE_MODULES = [
    ("overview", "Overview"),
    ("functionality", "Functionality"),
    ("mapping", "Mapping"),
    ("styles", "Styles"),
    ("utilities", "Utilities"),
    ("modules", "Modules"),
]

OPTIONAL_MODULE_LABELS = {
    "api": "API",
    "tester": "Controller Tester",
}


def hide_console_window():
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window:
            ctypes.windll.user32.ShowWindow(console_window, 0)
    except (AttributeError, OSError):
        pass


class ControllerMouseOverlayApp:
    def __init__(self):
        self.running = True
        self.overlay_active = False
        self.holding_active = False
        self.status_text = "Initializing..."
        self.active_page = "overview"
        self.selected_input = "BTN_SOUTH"
        self.overlay_width = 1180
        self.overlay_height = 760
        self.overlay_current_y = -self.overlay_height - 30
        self.overlay_target_y = self.overlay_current_y
        self.first_launch = not os.path.exists(SETTINGS_PATH)
        self.controller_connected = False
        self.controller_warning_shown = False
        self.controller_disconnect_time = None
        self.controller_warning_timeout = 2.0  # Show warning after 2 seconds of no controller
        self.no_controller_overlay_shown = False  # Track if we've shown overlay for no controller
        self.startup_check_time = None
        self.controller_name = None  # Track detected controller name
        self.last_controller_check = 0  # Track last controller name check time
        self.last_overlay_toggle_at = 0.0
        self.runtime_flags = {
            "movement_enabled": False,
            "control_windows": False,
            "auto_enable_movement": False,
            "auto_hold_enabled": False,
        }

        self.controller_state = ControllerState()
        self.button_states = {name: 0 for name in SUPPORTED_INPUTS}
        self.settings = self.load_settings()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Controller Mouse Overlay")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg=COLORS["bg"], highlightthickness=1, highlightbackground=COLORS["border"])

        self.page_frames = {}
        self.page_buttons = {}
        self.functionality_value_labels = {}
        self.toggle_buttons = {}
        self.listening_for_input = False
        self.mapping_grid_buttons = {}
        self.style_vars = {}
        self.loaded_optional_modules = set()
        self.loaded_community_modules = set()
        self.optional_modules = {}
        self.community_modules = {}
        self.core_modules = {}
        self.module_errors = {}
        self.scrollbar_style_name = "Overlay.Vertical.TScrollbar"

        self.apply_loaded_style()
        self.load_core_modules()
        self.build_overlay()
        self.sync_ui_with_settings()
        self.update_page_visibility()
        self.position_overlay(initial=True)
        self.set_status("Waiting for controller...")
        self.startup_check_time = time.time()

        self.controller_thread = threading.Thread(target=self.controller_loop, daemon=True)
        self.controller_thread.start()

        self.root.after(16, self.tick)
        self.root.after(150, self.animate_overlay)
        self.root.after(2500, self.check_and_show_overlay_if_no_controller)  # Check after 2.5 seconds
        self.root.after(5000, self.periodic_controller_check)  # Check controller name every 5 seconds
        self.root.bind("<Escape>", lambda _event: self.stop())

    def load_settings(self):
        settings = deepcopy(DEFAULT_SETTINGS)
        os.makedirs(APP_DIR, exist_ok=True)
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                self.deep_update(settings, loaded)
            except (OSError, json.JSONDecodeError):
                pass
        self.normalize_settings(settings)
        self.apply_runtime_defaults(settings)
        return settings

    def save_settings(self):
        os.makedirs(APP_DIR, exist_ok=True)
        persisted = deepcopy(self.settings)
        for key in self.runtime_flags:
            persisted.pop(key, None)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(persisted, handle, indent=2)

    def deep_update(self, base, updates):
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self.deep_update(base[key], value)
            else:
                base[key] = value

    def normalize_settings(self, settings):
        settings["deadzone"] = float(clamp(settings.get("deadzone", 0.25), 0.0, 0.9))
        settings["strength"] = int(clamp(settings.get("strength", 50), 1, 300))
        settings["overlay_cursor_speed"] = int(clamp(settings.get("overlay_cursor_speed", 28), 5, 120))
        settings["edge_padding"] = int(clamp(settings.get("edge_padding", 80), 0, 500))
        settings["dpad_flip_y"] = bool(settings.get("dpad_flip_y", DEFAULT_SETTINGS["dpad_flip_y"]))

        if settings.get("input_mode") not in INPUT_MODE_LABELS:
            settings["input_mode"] = DEFAULT_SETTINGS["input_mode"]
        if settings.get("position_mode") not in POSITION_LABELS:
            settings["position_mode"] = DEFAULT_SETTINGS["position_mode"]
        if settings.get("custom_slot") not in ("custom_1", "custom_2", "custom_3"):
            settings["custom_slot"] = DEFAULT_SETTINGS["custom_slot"]
        if settings.get("auto_hold_action") not in AUTO_HOLD_OPTIONS:
            settings["auto_hold_action"] = DEFAULT_SETTINGS["auto_hold_action"]

        input_actions = settings.setdefault("input_actions", {})
        for input_name in SUPPORTED_INPUTS:
            action = input_actions.get(input_name, DEFAULT_SETTINGS["input_actions"].get(input_name, "none"))
            if action not in ACTION_DEFINITIONS:
                action = "none"
            input_actions[input_name] = action

        input_remaps = settings.setdefault("input_remaps", {})
        for input_name in SUPPORTED_INPUTS:
            remap = input_remaps.get(input_name, DEFAULT_SETTINGS["input_remaps"].get(input_name, "Right Click"))
            if remap not in WINDOWS_REMAP_OPTIONS:
                remap = DEFAULT_SETTINGS["input_remaps"][input_name]
            input_remaps[input_name] = remap

        style = settings.setdefault("style", {})
        settings["style"] = self.normalize_style_map(style)

        custom_locations = settings.setdefault("custom_locations", {})
        for slot, default_position in DEFAULT_SETTINGS["custom_locations"].items():
            position = custom_locations.get(slot, {})
            custom_locations[slot] = {
                "x": int(position.get("x", default_position["x"])),
                "y": int(position.get("y", default_position["y"])),
            }

    def apply_runtime_defaults(self, settings):
        for key, default in self.runtime_flags.items():
            settings[key] = default

    def normalize_style_map(self, style_map):
        normalized = {}
        for key, default_value in DEFAULT_SETTINGS["style"].items():
            value = style_map.get(key, default_value)
            if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
                value = default_value
            normalized[key] = value
        return normalized

    def apply_loaded_style(self):
        style_map = self.settings.get("style", DEFAULT_SETTINGS["style"])
        COLORS.update(style_map)

    def apply_style_config(self, style_map):
        self.settings["style"] = self.normalize_style_map(style_map)
        COLORS.update(self.settings["style"])
        self.save_settings()
        self.rebuild_overlay()

    def load_core_modules(self):
        self.core_modules = {}
        self.module_errors = {}
        for registry_name, _display_name in CORE_MODULES:
            try:
                module, info = load_registered_module(CORE_MODULES_DIR, registry_name)
                self.core_modules[registry_name] = module
                self.module_errors.pop(registry_name, None)
            except ModuleLoadError as exc:
                self.core_modules[registry_name] = None
                self.module_errors[registry_name] = str(exc)

    def build_overlay(self):
        self.outer = tk.Frame(self.overlay, bg=COLORS["bg"], padx=18, pady=18)
        self.outer.pack(fill="both", expand=True)

        self.header = tk.Frame(self.outer, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
        self.header.pack(fill="x")

        title_block = tk.Frame(self.header, bg=COLORS["panel"])
        title_block.pack(side="left", anchor="w")

        tk.Label(
            title_block,
            text="Controller Overlay",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w")

        tk.Label(
            title_block,
            text="Animated top overlay for controller-driven cursor control and mapping.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        self.status_badge = tk.Label(
            self.header,
            text="",
            bg=COLORS["card"],
            fg=COLORS["accent"],
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )

        header_controls = tk.Frame(self.header, bg=COLORS["panel_alt"], padx=4, pady=4, highlightthickness=1, highlightbackground=COLORS["border"])
        header_controls.place(relx=1.0, rely=0.0, anchor="ne", x=25, y=-25)

        tk.Button(
            header_controls,
            text="X",
            command=self.stop,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            bg=COLORS["card"],
            fg=COLORS["danger"],
            activebackground=COLORS["danger"],
            activeforeground=COLORS["text"],
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            header_controls,
            text="-",
            command=self.hide_overlay,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            activebackground=COLORS["card_alt"],
            activeforeground=COLORS["text"],
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
        ).pack(side="right", padx=(0, 4))

        self.status_badge.pack(side="right", padx=(0, 8))

        nav = tk.Frame(self.outer, bg=COLORS["bg"], pady=16)
        nav.pack(fill="x")

        tk.Label(nav, text="Core", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=(0, 8))
        for key, label in CORE_MODULES:
            button = tk.Button(
                nav,
                text=label,
                command=lambda page=key: self.set_active_page(page),
                relief="flat",
                bd=0,
                padx=18,
                pady=10,
                font=("Segoe UI Semibold", 10),
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 10))
            self.page_buttons[key] = button

        tk.Label(nav, text="Tools", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=(12, 8))
        self.tools_nav = nav

        self.content_shell = tk.Frame(self.outer, bg=COLORS["bg"])
        self.content_shell.pack(fill="both", expand=True)

        self.content_canvas = tk.Canvas(
            self.content_shell,
            bg=COLORS["bg"],
            bd=0,
            highlightthickness=0,
        )
        self.content_scrollbar = self.create_themed_scrollbar(self.content_shell, self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)
        self.content_scrollbar.pack(side="right", fill="y")
        self.content_canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.content_canvas, bg=COLORS["bg"])
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self.on_content_configure)
        self.content_canvas.bind("<Configure>", self.on_canvas_configure)
        self.bind_mousewheel(self.content_canvas)

        for key, _label in CORE_MODULES:
            self.page_frames[key] = self.build_core_module_page(key, self.content)
        for module_name in sorted(self.loaded_optional_modules):
            self.load_optional_module(module_name, activate=False)
        for module_name in sorted(self.loaded_community_modules):
            self.load_community_module(module_name, activate=False)

    def rebuild_overlay(self):
        if hasattr(self, "outer") and self.outer.winfo_exists():
            self.outer.destroy()
        self.page_frames = {}
        self.page_buttons = {}
        self.functionality_value_labels = {}
        self.toggle_buttons = {}
        self.mapping_grid_buttons = {}
        self.style_vars = {}
        self.optional_modules = {}
        self.community_modules = {}
        self.load_core_modules()
        self.build_overlay()
        self.sync_ui_with_settings()
        self.update_page_visibility()
        self.position_overlay()

    def build_overview_page(self, parent):
        return self.build_core_module_page("overview", parent)
    def build_functionality_page(self, parent):
        return self.build_core_module_page("functionality", parent)
    def build_mapping_page(self, parent):
        return self.build_core_module_page("mapping", parent)
    def build_tester_page(self, parent):
        return self.load_optional_module_page("tester", parent)
    def build_styles_page(self, parent):
        return self.build_core_module_page("styles", parent)
    def build_utility_page(self, parent):
        return self.build_core_module_page("utilities", parent)
    def build_utility_button(self, parent, text, command, bg=None):
        module = self.core_modules.get("utilities")
        if module and hasattr(module, "build_button"):
            return module.build_button(self, parent, text, command, bg)
        return self.build_basic_button(parent, text, command, bg)

    def build_core_module_page(self, registry_name, parent):
        module = self.core_modules.get(registry_name)
        if module and hasattr(module, "build_page"):
            try:
                return module.build_page(self, parent)
            except Exception as exc:
                self.module_errors[registry_name] = f"Module failed while opening: {exc}"
        return self.build_missing_module_page(parent, registry_name)

    def build_missing_module_page(self, parent, registry_name):
        frame = tk.Frame(parent, bg=COLORS["bg"])
        card = tk.Frame(frame, bg=COLORS["panel"], padx=22, pady=20, highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True)

        display_name = dict(CORE_MODULES).get(registry_name, registry_name.replace("_", " ").title())
        tk.Label(card, text=f"{display_name} Module Missing", bg=COLORS["panel"], fg=COLORS["danger"], font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(
            card,
            text=(
                f"The core module '{registry_name}' could not be found or loaded. "
                "The app can keep running, but this control panel module must be located before its controls are available."
            ),
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(10, 8))

        expected = os.path.join(CORE_MODULES_DIR, f"#.#.#_{registry_name}_core", "module.py")
        tk.Label(card, text=f"Expected layout pattern: {expected}", bg=COLORS["panel"], fg=COLORS["muted"], font=("Consolas", 10), wraplength=820, justify="left").pack(anchor="w", pady=(0, 8))

        error = self.module_errors.get(registry_name, "Module is not registered.")
        tk.Label(card, text=f"Loader message: {error}", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=760, justify="left").pack(anchor="w")
        self.build_basic_button(card, "Retry Loading Core Modules", self.retry_core_modules, bg=COLORS["card_alt"])
        return frame

    def build_basic_button(self, parent, text, command, bg=None):
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

    def retry_core_modules(self):
        self.rebuild_overlay()
        self.set_status("Core modules reloaded")
    def build_slider(self, parent, label, minimum, maximum, resolution, callback):
        section = tk.Frame(parent, bg=COLORS["panel"])
        section.pack(fill="x", pady=(14, 0))

        top = tk.Frame(section, bg=COLORS["panel"])
        top.pack(fill="x")

        tk.Label(top, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(side="left")
        value_label = tk.Label(top, text="", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Semibold", 10))
        value_label.pack(side="right")
        self.functionality_value_labels[label] = value_label

        scale = tk.Scale(
            section,
            from_=minimum,
            to=maximum,
            resolution=resolution,
            orient="horizontal",
            command=lambda _value: callback(),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            activebackground=COLORS["accent_alt"],
            troughcolor=COLORS["card_alt"],
            highlightthickness=0,
            bd=0,
            length=420,
        )
        scale.pack(fill="x", pady=(8, 0))
        return scale

    def build_choice_row(self, parent, title, setting_key, mapping, callback):
        row = tk.Frame(parent, bg=COLORS["card_alt"])
        row.pack(fill="x", pady=(10, 0))

        top = tk.Frame(row, bg=COLORS["card_alt"])
        top.pack(fill="x")

        tk.Label(top, text=title, bg=COLORS["card_alt"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(side="left")
        value_label = tk.Label(top, text="", bg=COLORS["card_alt"], fg=COLORS["accent"], font=("Segoe UI Semibold", 10))
        value_label.pack(side="right")
        self.functionality_mode_labels[setting_key] = value_label

        choices = tk.Frame(row, bg=COLORS["card_alt"])
        choices.pack(fill="x", pady=(8, 0))

        for index, (key, label) in enumerate(mapping.items()):
            button = tk.Button(
                choices,
                text=label if isinstance(label, str) else key,
                command=lambda chosen_key=key: callback(chosen_key),
                relief="flat",
                bd=0,
                padx=12,
                pady=9,
                bg=COLORS["panel_alt"],
                fg=COLORS["text"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                font=("Segoe UI", 9),
                cursor="hand2",
                wraplength=110,
                justify="center",
            )
            button.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 8), pady=(0, 8))

        for column in range(3):
            choices.grid_columnconfigure(column, weight=1)

    def load_optional_module_page(self, module_name, parent):
        try:
            module, _info = load_registered_module(OPTIONAL_MODULES_DIR, module_name)
        except ModuleLoadError as exc:
            self.module_errors[module_name] = str(exc)
            return self.build_optional_module_error_page(parent, module_name)
        self.optional_modules[module_name] = module
        return module.build_page(self, parent)

    def load_optional_module(self, module_name, activate=True):
        if module_name not in self.page_frames:
            self.page_frames[module_name] = self.load_optional_module_page(module_name, self.content)
            self.loaded_optional_modules.add(module_name)
            self.add_optional_module_button(module_name)
        if activate:
            self.set_active_page(module_name)
            self.set_status(f"Loaded {module_name.replace('_', ' ').title()} module")
        self.refresh_modules_page()

    def unload_optional_module(self, module_name):
        frame = self.page_frames.pop(module_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        button = self.page_buttons.pop(module_name, None)
        if button is not None and button.winfo_exists():
            button.destroy()
        self.optional_modules.pop(module_name, None)
        self.loaded_optional_modules.discard(module_name)
        if self.active_page == module_name:
            self.active_page = "modules" if "modules" in self.page_frames else "overview"
        self.update_page_visibility()
        self.set_status(f"Unloaded {module_name.replace('_', ' ').title()} module")
        self.refresh_modules_page()

    def reload_optional_module(self, module_name, activate=False):
        frame = self.page_frames.pop(module_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        self.optional_modules.pop(module_name, None)
        self.loaded_optional_modules.discard(module_name)
        self.page_frames[module_name] = self.load_optional_module_page(module_name, self.content)
        self.loaded_optional_modules.add(module_name)
        self.add_optional_module_button(module_name)
        if activate or self.active_page == module_name:
            self.set_active_page(module_name)
        else:
            self.update_page_visibility()
        self.set_status(f"Reloaded {module_name.replace('_', ' ').title()} module")
        self.refresh_modules_page()

    def reload_all_optional_modules(self):
        loaded_modules = sorted(self.loaded_optional_modules)
        if not loaded_modules:
            self.set_status("No additional modules are loaded")
            self.refresh_modules_page()
            return
        active_page = self.active_page
        for module_name in loaded_modules:
            frame = self.page_frames.pop(module_name, None)
            if frame is not None and frame.winfo_exists():
                frame.destroy()
            self.optional_modules.pop(module_name, None)
            self.loaded_optional_modules.discard(module_name)
            self.page_frames[module_name] = self.load_optional_module_page(module_name, self.content)
            self.loaded_optional_modules.add(module_name)
            self.add_optional_module_button(module_name)
        if active_page in self.page_frames:
            self.active_page = active_page
        self.update_page_visibility()
        self.set_status(f"Reloaded {len(loaded_modules)} additional module(s)")
        self.refresh_modules_page()

    def load_community_module_page(self, module_name, parent):
        try:
            module, _info = load_registered_module(COMMUNITY_MODULES_DIR, module_name)
        except ModuleLoadError as exc:
            self.module_errors[module_name] = str(exc)
            return self.build_optional_module_error_page(parent, module_name, category_label="community")
        self.community_modules[module_name] = module
        return module.build_page(self, parent)

    def load_community_module(self, module_name, activate=True):
        if module_name not in self.page_frames:
            self.page_frames[module_name] = self.load_community_module_page(module_name, self.content)
            self.loaded_community_modules.add(module_name)
            self.add_optional_module_button(module_name)
        if activate:
            self.set_active_page(module_name)
            self.set_status(f"Loaded {module_name.replace('_', ' ').title()} community module")
        self.refresh_modules_page()

    def unload_community_module(self, module_name):
        frame = self.page_frames.pop(module_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        button = self.page_buttons.pop(module_name, None)
        if button is not None and button.winfo_exists():
            button.destroy()
        self.community_modules.pop(module_name, None)
        self.loaded_community_modules.discard(module_name)
        if self.active_page == module_name:
            self.active_page = "modules" if "modules" in self.page_frames else "overview"
        self.update_page_visibility()
        self.set_status(f"Unloaded {module_name.replace('_', ' ').title()} community module")
        self.refresh_modules_page()

    def reload_community_module(self, module_name, activate=False):
        frame = self.page_frames.pop(module_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        self.community_modules.pop(module_name, None)
        self.loaded_community_modules.discard(module_name)
        self.page_frames[module_name] = self.load_community_module_page(module_name, self.content)
        self.loaded_community_modules.add(module_name)
        self.add_optional_module_button(module_name)
        if activate or self.active_page == module_name:
            self.set_active_page(module_name)
        else:
            self.update_page_visibility()
        self.set_status(f"Reloaded {module_name.replace('_', ' ').title()} community module")
        self.refresh_modules_page()

    def reload_all_community_modules(self):
        loaded_modules = sorted(self.loaded_community_modules)
        if not loaded_modules:
            self.set_status("No community modules are loaded")
            self.refresh_modules_page()
            return
        active_page = self.active_page
        for module_name in loaded_modules:
            frame = self.page_frames.pop(module_name, None)
            if frame is not None and frame.winfo_exists():
                frame.destroy()
            self.community_modules.pop(module_name, None)
            self.loaded_community_modules.discard(module_name)
            self.page_frames[module_name] = self.load_community_module_page(module_name, self.content)
            self.loaded_community_modules.add(module_name)
            self.add_optional_module_button(module_name)
        if active_page in self.page_frames:
            self.active_page = active_page
        self.update_page_visibility()
        self.set_status(f"Reloaded {len(loaded_modules)} community module(s)")
        self.refresh_modules_page()

    def load_core_module(self, registry_name, activate=True):
        if registry_name == "core":
            self.set_status("Core is required and already loaded")
            self.refresh_modules_page()
            return
        try:
            module, _info = load_registered_module(CORE_MODULES_DIR, registry_name)
        except ModuleLoadError as exc:
            self.core_modules[registry_name] = None
            self.module_errors[registry_name] = str(exc)
            self.set_status(f"Could not load {registry_name.replace('_', ' ').title()} module")
            self.refresh_modules_page()
            return

        self.core_modules[registry_name] = module
        self.module_errors.pop(registry_name, None)
        frame = self.page_frames.pop(registry_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        self.page_frames[registry_name] = self.build_core_module_page(registry_name, self.content)
        if activate:
            self.set_active_page(registry_name)
        else:
            self.update_page_visibility()
        self.set_status(f"Loaded {registry_name.replace('_', ' ').title()} module")
        if registry_name != "modules":
            self.refresh_modules_page()

    def unload_core_module(self, registry_name):
        if registry_name == "core":
            self.set_status("Core is required and cannot be unloaded")
            return
        if registry_name == "modules":
            self.set_status("Modules page stays loaded so modules can be managed")
            return
        self.core_modules[registry_name] = None
        self.module_errors[registry_name] = "Module was unloaded from the Modules page."
        frame = self.page_frames.pop(registry_name, None)
        if frame is not None and frame.winfo_exists():
            frame.destroy()
        self.page_frames[registry_name] = self.build_missing_module_page(self.content, registry_name)
        if self.active_page == registry_name:
            self.active_page = "modules"
        self.update_page_visibility()
        self.set_status(f"Unloaded {registry_name.replace('_', ' ').title()} module")
        self.refresh_modules_page()

    def discover_module_metadata(self):
        try:
            core_info = read_module_info(CORE_DIR)
        except ModuleLoadError as exc:
            core_info = {
                "version": "Unknown",
                "display_name": "Core",
                "registry_name": "core",
                "description": f"Required core metadata could not be read: {exc}",
                "creators": [],
            }
        return {
            "core": [{"folder": "core", "path": CORE_DIR, "info": core_info}] + discover_registered_modules(CORE_MODULES_DIR),
            "optional": discover_registered_modules(OPTIONAL_MODULES_DIR),
            "community": discover_registered_modules(COMMUNITY_MODULES_DIR),
        }

    def add_optional_module_button(self, module_name):
        if module_name in self.page_buttons:
            return
        label = OPTIONAL_MODULE_LABELS.get(module_name, module_name.replace("_", " ").title())
        button = tk.Button(
            self.tools_nav,
            text=label,
            command=lambda page=module_name: self.set_active_page(page),
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        )
        button.pack(side="left", padx=(0, 10))
        self.page_buttons[module_name] = button
        self.update_page_visibility()

    def refresh_optional_module(self, module_name):
        module = self.optional_modules.get(module_name)
        if module and hasattr(module, "refresh"):
            return module.refresh(self)

    def refresh_community_module(self, module_name):
        module = self.community_modules.get(module_name)
        if module and hasattr(module, "refresh"):
            return module.refresh(self)

    def build_optional_module_error_page(self, parent, module_name, category_label="additional"):
        frame = tk.Frame(parent, bg=COLORS["bg"])
        card = tk.Frame(frame, bg=COLORS["panel"], padx=22, pady=20, highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True)
        label = OPTIONAL_MODULE_LABELS.get(module_name, module_name.replace("_", " ").title())
        tk.Label(card, text=f"{label} Module Missing", bg=COLORS["panel"], fg=COLORS["danger"], font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(
            card,
            text=(
                f"This {category_label} module could not be found. "
                "It must be inside a named module folder with module.py and info.json."
            ),
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 10),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(10, 8))
        tk.Label(card, text=f"Loader message: {self.module_errors.get(module_name, 'Module is not registered.')}", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=760, justify="left").pack(anchor="w")
        return frame

    def build_mapping_grid(self):
        module = self.core_modules.get("mapping")
        if module and hasattr(module, "build_grid"):
            return module.build_grid(self)
    def select_input(self, input_name):
        self.selected_input = input_name
        self.listening_for_input = False
        self.listen_status_label.config(text="")
        self.refresh_mapping_editor()
        self.refresh_mapping_grid()

    def start_input_listen(self):
        self.listening_for_input = True
        self.listen_status_label.config(text="Press any controller input...")

    def sync_ui_with_settings(self):
        if hasattr(self, "deadzone_scale"):
            self.deadzone_scale.set(self.settings["deadzone"])
            self.strength_scale.set(self.settings["strength"])
            self.overlay_speed_scale.set(self.settings["overlay_cursor_speed"])
            self.edge_padding_scale.set(self.settings["edge_padding"])

        if self.first_launch:
            self.status_text = "First launch: all mappings start as No Action"
        self.refresh_status_badge()
        self.refresh_overview()
        self.refresh_functionality()
        self.refresh_mapping_editor()
        self.refresh_tester()
        self.refresh_mapping_grid()
        self.refresh_style_editor()
        self.save_settings()

    def refresh_status_badge(self):
        self.status_badge.config(
            text=(
                f"{self.status_text}  |  "
                f"Movement Lock {'On' if self.settings['movement_enabled'] else 'Off'}  |  "
                f"Control Windows {'On' if self.settings['control_windows'] else 'Off'}  |  "
                f"Overlay {'Open' if self.overlay_active else 'Closed'}"
            )
        )

    def refresh_overview(self):
        return self.refresh_core_module("overview")
    def refresh_functionality(self):
        return self.refresh_core_module("functionality")
    def refresh_tester(self):
        return self.refresh_optional_module("tester")
    def refresh_mapping_editor(self):
        return self.refresh_core_module("mapping", "refresh_editor")
    def refresh_mapping_grid(self):
        return self.refresh_core_module("mapping", "refresh_grid")
    def refresh_style_editor(self):
        return self.refresh_core_module("styles")
    def refresh_modules_page(self):
        return self.refresh_core_module("modules")

    def refresh_core_module(self, registry_name, refresh_name="refresh"):
        module = self.core_modules.get(registry_name)
        if module and hasattr(module, refresh_name):
            try:
                return getattr(module, refresh_name)(self)
            except (tk.TclError, AttributeError):
                return None
    def update_page_visibility(self):
        if self.active_page not in self.page_frames:
            self.active_page = "overview"
        for key, frame in self.page_frames.items():
            if key == self.active_page:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        self.content_canvas.yview_moveto(0)

        for key, button in self.page_buttons.items():
            active = key == self.active_page
            button.config(
                bg=COLORS["accent_alt"] if active else COLORS["panel"],
                fg=COLORS["text"],
                activebackground=COLORS["accent_alt"] if active else COLORS["card"],
                activeforeground=COLORS["text"],
            )

    def set_active_page(self, page_name):
        self.active_page = page_name
        self.update_page_visibility()

    def set_status(self, text):
        self.status_text = text
        self.refresh_status_badge()

    def create_themed_scrollbar(self, parent, command):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            self.scrollbar_style_name,
            background=COLORS["card"],
            troughcolor=COLORS["panel"],
            bordercolor=COLORS["border"],
            arrowcolor=COLORS["text"],
            darkcolor=COLORS["card"],
            lightcolor=COLORS["card"],
            gripcount=0,
            relief="flat",
            borderwidth=0,
            arrowsize=14,
        )
        style.map(
            self.scrollbar_style_name,
            background=[("active", COLORS["accent_alt"])],
            arrowcolor=[("active", COLORS["text"])],
        )
        return ttk.Scrollbar(parent, orient="vertical", command=command, style=self.scrollbar_style_name)

    def on_content_configure(self, _event):
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.content_canvas.itemconfigure(self.content_window, width=event.width)

    def on_mousewheel(self, event):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.content_canvas.yview_scroll(delta, "units")

    def on_action_list_mousewheel(self, event):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.action_listbox.yview_scroll(delta, "units")
        return "break"

    def on_remap_list_mousewheel(self, event):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if delta:
            self.remap_listbox.yview_scroll(delta, "units")
        return "break"

    def bind_mousewheel(self, widget):
        widget.bind_all("<MouseWheel>", self.on_mousewheel)
        widget.bind_all("<Button-4>", self.on_mousewheel)
        widget.bind_all("<Button-5>", self.on_mousewheel)

    def position_overlay(self, initial=False):
        screen_w = win32api.GetSystemMetrics(0)
        x = max(0, (screen_w - self.overlay_width) // 2)
        if initial:
            self.overlay.geometry(f"{self.overlay_width}x{self.overlay_height}+{x}+{int(self.overlay_current_y)}")
        else:
            self.overlay.geometry(f"{self.overlay_width}x{self.overlay_height}+{x}+{int(self.overlay_current_y)}")

    def animate_overlay(self):
        if not self.running:
            return

        distance = self.overlay_target_y - self.overlay_current_y
        if abs(distance) > 1:
            self.overlay_current_y += distance * 0.28
            if abs(distance) < 4:
                self.overlay_current_y = self.overlay_target_y
        else:
            self.overlay_current_y = self.overlay_target_y

        self.position_overlay()

        if not self.overlay_active and self.overlay_current_y <= -self.overlay_height + 2:
            self.overlay.withdraw()

        self.root.after(16, self.animate_overlay)

    def toggle_overlay(self):
        now = time.time()
        # Ignore duplicate toggle requests that arrive in the same input burst.
        if now - self.last_overlay_toggle_at < 0.22:
            return
        self.last_overlay_toggle_at = now

        self.overlay_active = not self.overlay_active
        if self.overlay_active:
            self.overlay.deiconify()
            self.overlay.lift()
            self.overlay.focus_force()
            self.overlay_target_y = 18
            self.set_status("Overlay opened")
        else:
            self.overlay_target_y = -self.overlay_height - 24
            self.set_status("Overlay closed")
        self.refresh_status_badge()

    def hide_overlay(self):
        if not self.overlay_active:
            return
        self.overlay_active = False
        self.overlay_target_y = -self.overlay_height - 24
        self.set_status("Overlay hidden")
        self.refresh_status_badge()

    def hide_overlay_on_controller_connect(self):
        """Hide the overlay when controller connects after being shown due to no controller"""
        if self.overlay_active and self.no_controller_overlay_shown:
            self.overlay_active = False
            self.overlay_target_y = -self.overlay_height - 24
            self.refresh_status_badge()

    def on_action_list_select(self, _event):
        if not self.action_listbox.curselection():
            return
        selected_index = self.action_listbox.curselection()[0]
        action_key = ACTION_KEYS[selected_index]
        if self.settings["input_actions"][self.selected_input] == action_key:
            self.action_description_label.config(text=self.describe_action_detail(self.selected_input))
            return
        self.settings["input_actions"][self.selected_input] = action_key
        self.persist_settings(f"{INPUT_LABELS[self.selected_input]} mapped to {self.describe_action(self.selected_input)}")

    def on_remap_list_select(self, _event):
        if not self.remap_listbox.curselection():
            return
        selected_index = self.remap_listbox.curselection()[0]
        remap_name = list(WINDOWS_REMAP_OPTIONS.keys())[selected_index]
        if self.settings["input_remaps"][self.selected_input] == remap_name:
            return
        self.settings["input_remaps"][self.selected_input] = remap_name
        self.persist_settings(f"{INPUT_LABELS[self.selected_input]} remap set to {remap_name}")

    def persist_settings(self, status=None):
        self.normalize_settings(self.settings)
        self.save_settings()
        if status:
            self.status_text = status
        self.refresh_status_badge()
        self.refresh_overview()
        self.refresh_functionality()
        self.refresh_mapping_editor()
        self.refresh_tester()
        self.refresh_mapping_grid()
        self.refresh_style_editor()

    def export_settings(self):
        os.makedirs(EXPORT_DIR, exist_ok=True)
        export_path = os.path.join(EXPORT_DIR, "exported_settings.json")
        exported = deepcopy(self.settings)
        for key, value in self.runtime_flags.items():
            exported[key] = value
        with open(export_path, "w", encoding="utf-8") as handle:
            json.dump(exported, handle, indent=2)
        self.set_status(f"Exported settings to {export_path}")

    def import_settings(self):
        path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=EXPORT_DIR if os.path.isdir(EXPORT_DIR) else APP_DIR,
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.set_status("Settings import failed")
            return
        imported = deepcopy(DEFAULT_SETTINGS)
        self.deep_update(imported, data)
        self.normalize_settings(imported)
        self.apply_runtime_defaults(imported)
        self.first_launch = False
        self.settings = imported
        self.apply_loaded_style()
        self.save_settings()
        self.rebuild_overlay()
        self.set_status(f"Imported settings from {path}")

    def open_export_folder(self):
        os.makedirs(STYLE_EXPORT_DIR, exist_ok=True)
        os.makedirs(CONTROL_SHEET_EXPORT_DIR, exist_ok=True)
        try:
            os.startfile(EXPORT_DIR)
            self.set_status(f"Opened export folder at {EXPORT_DIR}")
        except OSError:
            self.set_status(f"Export folder is {EXPORT_DIR}")

    def export_current_style(self):
        os.makedirs(STYLE_EXPORT_DIR, exist_ok=True)
        path = os.path.join(STYLE_EXPORT_DIR, "current_style.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.settings["style"], handle, indent=2)
        self.set_status(f"Exported current style to {path}")

    def export_default_style(self):
        os.makedirs(STYLE_EXPORT_DIR, exist_ok=True)
        path = os.path.join(STYLE_EXPORT_DIR, "default_style.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(DEFAULT_SETTINGS["style"], handle, indent=2)
        self.set_status(f"Exported default style to {path}")

    def export_control_sheet(self):
        os.makedirs(CONTROL_SHEET_EXPORT_DIR, exist_ok=True)
        path = os.path.join(CONTROL_SHEET_EXPORT_DIR, "control_sheet.json")
        payload = {
            "input_actions": self.settings["input_actions"],
            "input_remaps": self.settings["input_remaps"],
            "input_mode": self.settings["input_mode"],
            "dpad_flip_y": self.settings["dpad_flip_y"],
            "position_mode": self.settings["position_mode"],
            "custom_slot": self.settings["custom_slot"],
            "custom_locations": self.settings["custom_locations"],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        self.set_status(f"Exported control sheet to {path}")

    def import_style(self):
        path = filedialog.askopenfilename(
            title="Import Style",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=STYLE_EXPORT_DIR if os.path.isdir(STYLE_EXPORT_DIR) else APP_DIR,
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.set_status("Style import failed")
            return
        merged = deepcopy(self.settings["style"])
        merged.update(data)
        self.settings["style"] = self.normalize_style_map(merged)
        self.apply_style_config(self.settings["style"])
        self.set_status(f"Imported style from {path}")

    def import_control_sheet(self):
        path = filedialog.askopenfilename(
            title="Import Control Sheet",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=CONTROL_SHEET_EXPORT_DIR if os.path.isdir(CONTROL_SHEET_EXPORT_DIR) else APP_DIR,
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.set_status("Control sheet import failed")
            return
        for key in ["input_actions", "input_remaps", "input_mode", "dpad_flip_y", "position_mode", "custom_slot", "custom_locations"]:
            if key in data:
                self.settings[key] = data[key]
        self.normalize_settings(self.settings)
        self.persist_settings(f"Imported control sheet from {path}")

    def apply_style_from_editor(self):
        updated = deepcopy(self.settings["style"])
        for key, var in self.style_vars.items():
            updated[key] = var.get().strip()
        self.settings["style"] = self.normalize_style_map(updated)
        self.apply_style_config(self.settings["style"])
        self.set_status("Applied current style")

    def clear_data(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                os.remove(SETTINGS_PATH)
            except OSError:
                self.set_status("Clear data failed")
                return
        self.first_launch = True
        self.settings = deepcopy(DEFAULT_SETTINGS)
        self.normalize_settings(self.settings)
        self.apply_runtime_defaults(self.settings)
        self.button_states = {name: 0 for name in SUPPORTED_INPUTS}
        self.controller_state = ControllerState()
        self.selected_input = "BTN_SOUTH"
        self.sync_ui_with_settings()
        self.overlay_active = True
        self.overlay_target_y = 18
        self.overlay.deiconify()
        self.overlay.lift()
        self.set_status("Saved data cleared")

    def on_off(self, value):
        return "On" if value else "Off"

    def action_short_label(self, action_key):
        label = ACTION_DEFINITIONS[action_key][0]
        return label if len(label) <= 13 else label[:12] + "."

    def describe_action(self, input_name):
        action_key = self.settings["input_actions"][input_name]
        action_name = ACTION_DEFINITIONS[action_key][0]
        if action_key == "windows_remap":
            return f"{action_name}: {self.settings['input_remaps'][input_name]}"
        return action_name

    def describe_action_detail(self, input_name):
        action_key = self.settings["input_actions"][input_name]
        base_description = ACTION_DEFINITIONS[action_key][1]
        if action_key == "windows_remap":
            return f"{base_description} Current output: {self.settings['input_remaps'][input_name]}."
        return base_description

    def inputs_for_action(self, action_key):
        matches = [INPUT_LABELS[name] for name, action in self.settings["input_actions"].items() if action == action_key]
        return ", ".join(matches) if matches else "None"

    def toggle_setting(self, key):
        self.settings[key] = not self.settings[key]
        labels = {
            "movement_enabled": "Movement Lock",
            "auto_enable_movement": "Auto Enable Movement Lock",
            "dpad_flip_y": "Flip D-Pad Y",
        }
        self.persist_settings(f"{labels.get(key, key.replace('_', ' ').title())} updated")

    def on_deadzone_change(self):
        self.settings["deadzone"] = float(self.deadzone_scale.get())
        self.persist_settings()

    def on_strength_change(self):
        self.settings["strength"] = int(float(self.strength_scale.get()))
        self.persist_settings()

    def on_overlay_speed_change(self):
        self.settings["overlay_cursor_speed"] = int(float(self.overlay_speed_scale.get()))
        self.persist_settings()

    def on_edge_padding_change(self):
        self.settings["edge_padding"] = int(float(self.edge_padding_scale.get()))
        self.persist_settings()

    def set_input_mode(self, value):
        self.settings["input_mode"] = value
        self.persist_settings(f"Movement Lock input set to {INPUT_MODE_LABELS[value]}")

    def set_position_mode(self, value):
        self.settings["position_mode"] = value
        self.persist_settings(f"Lock position set to {POSITION_LABELS[value]}")

    def set_custom_slot(self, value):
        self.settings["custom_slot"] = value
        self.persist_settings(f"Active custom slot set to {POSITION_LABELS[value]}")

    def set_auto_hold_action(self, value):
        if self.holding_active:
            self.perform_auto_hold_up()
            self.holding_active = False
        self.settings["auto_hold_action"] = value
        self.persist_settings(f"Auto hold action set to {value}")

    def capture_custom_location(self):
        x, y = win32api.GetCursorPos()
        slot = self.settings["custom_slot"]
        self.settings["custom_locations"][slot] = {"x": int(x), "y": int(y)}
        self.persist_settings(f"Saved current cursor to {POSITION_LABELS[slot]}")

    def get_screen(self):
        width = win32api.GetSystemMetrics(0)
        height = win32api.GetSystemMetrics(1)
        return width, height, width // 2, height // 2

    def get_virtual_screen_bounds(self):
        left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        return left, top, left + width - 1, top + height - 1

    def set_cursor(self, x, y):
        win32api.SetCursorPos((int(x), int(y)))

    def apply_deadzone(self, value):
        deadzone = self.settings["deadzone"]
        if abs(value) < deadzone:
            return 0.0
        if value > 0:
            return (value - deadzone) / (1 - deadzone)
        return (value + deadzone) / (1 - deadzone)

    def normalize_trigger(self, value):
        return clamp(float(value) / 255.0, 0.0, 1.0)

    def get_anchor_position(self):
        width, height, center_x, center_y = self.get_screen()
        pad = self.settings["edge_padding"]
        mode = self.settings["position_mode"]
        if mode == "center":
            return center_x, center_y
        if mode == "top_left":
            return pad, pad
        if mode == "top_right":
            return width - pad, pad
        if mode == "bottom_left":
            return pad, height - pad
        if mode == "bottom_right":
            return width - pad, height - pad
        custom = self.settings["custom_locations"][mode]
        return custom["x"], custom["y"]

    def get_active_motion(self):
        input_mode = self.settings["input_mode"]
        if input_mode == "left_stick":
            return self.controller_state.lx, self.controller_state.ly
        if input_mode == "right_stick":
            return self.controller_state.rx, self.controller_state.ry
        dpad_y = -self.controller_state.dpad_y if self.settings["dpad_flip_y"] else self.controller_state.dpad_y
        return float(self.controller_state.dpad_x), float(dpad_y)

    def is_idle(self):
        x_value, y_value = self.get_active_motion()
        return abs(x_value) < 0.01 and abs(y_value) < 0.01

    def perform_auto_hold_down(self):
        hold_type, value = AUTO_HOLD_OPTIONS[self.settings["auto_hold_action"]]
        if hold_type == "mouse":
            flag = {
                "left": win32con.MOUSEEVENTF_LEFTDOWN,
                "right": win32con.MOUSEEVENTF_RIGHTDOWN,
                "middle": win32con.MOUSEEVENTF_MIDDLEDOWN,
            }[value]
            win32api.mouse_event(flag, 0, 0)
        else:
            win32api.keybd_event(value, 0, 0, 0)

    def perform_auto_hold_up(self):
        hold_type, value = AUTO_HOLD_OPTIONS[self.settings["auto_hold_action"]]
        if hold_type == "mouse":
            flag = {
                "left": win32con.MOUSEEVENTF_LEFTUP,
                "right": win32con.MOUSEEVENTF_RIGHTUP,
                "middle": win32con.MOUSEEVENTF_MIDDLEUP,
            }[value]
            win32api.mouse_event(flag, 0, 0)
        else:
            win32api.keybd_event(value, 0, win32con.KEYEVENTF_KEYUP, 0)

    def update_auto_hold(self):
        should_hold = (
            self.settings["movement_enabled"]
            and self.settings["auto_hold_enabled"]
            and not self.overlay_active
            and not self.is_idle()
        )
        if should_hold and not self.holding_active:
            self.perform_auto_hold_down()
            self.holding_active = True
        elif not should_hold and self.holding_active:
            self.perform_auto_hold_up()
            self.holding_active = False

    def update_controller_movement(self):
        move_x, move_y = self.get_active_motion()

        if self.settings["auto_enable_movement"] and not self.overlay_active and (abs(move_x) > 0.01 or abs(move_y) > 0.01):
            if not self.settings["movement_enabled"]:
                self.settings["movement_enabled"] = True
                self.persist_settings("Movement Lock auto-enabled from controller input")

        if self.overlay_active:
            overlay_x, overlay_y = self.get_active_motion()
            if abs(overlay_x) < 0.01 and abs(overlay_y) < 0.01:
                return
            cursor_x, cursor_y = win32api.GetCursorPos()
            min_x, min_y, max_x, max_y = self.get_virtual_screen_bounds()
            next_x = clamp(cursor_x + (overlay_x * self.settings["overlay_cursor_speed"]), min_x, max_x)
            next_y = clamp(cursor_y + (overlay_y * self.settings["overlay_cursor_speed"]), min_y, max_y)
            self.set_cursor(next_x, next_y)
            return

        if self.settings["control_windows"]:
            if abs(move_x) < 0.01 and abs(move_y) < 0.01:
                return
            cursor_x, cursor_y = win32api.GetCursorPos()
            min_x, min_y, max_x, max_y = self.get_virtual_screen_bounds()
            next_x = clamp(cursor_x + (move_x * self.settings["overlay_cursor_speed"]), min_x, max_x)
            next_y = clamp(cursor_y + (move_y * self.settings["overlay_cursor_speed"]), min_y, max_y)
            self.set_cursor(next_x, next_y)
            return

        if not self.settings["movement_enabled"]:
            return

        anchor_x, anchor_y = self.get_anchor_position()
        self.set_cursor(anchor_x + (move_x * self.settings["strength"]), anchor_y + (move_y * self.settings["strength"]))

    def run_action(self, action_key, source_input=None):
        if action_key == "none":
            return

        if action_key == "toggle_overlay":
            self.root.after(0, self.toggle_overlay)
            return

        if self.overlay_active and action_key not in {"ui_click", "ui_scroll_up", "ui_scroll_down"}:
            return

        if action_key == "ui_click":
            if self.overlay_active:
                self.root.after(0, self.left_click)
            return
        if action_key == "ui_scroll_up":
            if self.overlay_active:
                self.root.after(0, lambda: self.content_canvas.yview_scroll(-3, "units"))
            return
        if action_key == "ui_scroll_down":
            if self.overlay_active:
                self.root.after(0, lambda: self.content_canvas.yview_scroll(3, "units"))
            return
        if action_key == "windows_remap":
            if source_input is not None:
                self.perform_windows_remap(self.settings["input_remaps"][source_input])
            return
        if action_key == "toggle_movement":
            self.settings["movement_enabled"] = not self.settings["movement_enabled"]
            self.root.after(0, lambda: self.persist_settings("Movement Lock toggled"))
            return
        if action_key == "enable_movement":
            self.settings["movement_enabled"] = True
            self.root.after(0, lambda: self.persist_settings("Movement Lock enabled"))
            return
        if action_key == "disable_movement":
            self.settings["movement_enabled"] = False
            self.root.after(0, lambda: self.persist_settings("Movement Lock disabled"))
            return
        if action_key == "toggle_control_windows":
            self.settings["control_windows"] = not self.settings["control_windows"]
            self.root.after(0, lambda: self.persist_settings("Control Windows toggled"))
            return
        if action_key == "enable_control_windows":
            self.settings["control_windows"] = True
            self.root.after(0, lambda: self.persist_settings("Control Windows enabled"))
            return
        if action_key == "disable_control_windows":
            self.settings["control_windows"] = False
            self.root.after(0, lambda: self.persist_settings("Control Windows disabled"))
            return
        if action_key == "toggle_auto_hold":
            self.settings["auto_hold_enabled"] = not self.settings["auto_hold_enabled"]
            self.root.after(0, lambda: self.persist_settings("Auto hold toggled"))
            return
        if action_key == "enable_auto_hold":
            self.settings["auto_hold_enabled"] = True
            self.root.after(0, lambda: self.persist_settings("Auto hold enabled"))
            return
        if action_key == "disable_auto_hold":
            self.settings["auto_hold_enabled"] = False
            self.root.after(0, lambda: self.persist_settings("Auto hold disabled"))
            return
        if action_key == "toggle_auto_enable_movement":
            self.settings["auto_enable_movement"] = not self.settings["auto_enable_movement"]
            self.root.after(0, lambda: self.persist_settings("Auto-enable movement lock toggled"))
            return
        if action_key == "enable_auto_enable_movement":
            self.settings["auto_enable_movement"] = True
            self.root.after(0, lambda: self.persist_settings("Auto-enable movement lock enabled"))
            return
        if action_key == "disable_auto_enable_movement":
            self.settings["auto_enable_movement"] = False
            self.root.after(0, lambda: self.persist_settings("Auto-enable movement lock disabled"))
            return
        if action_key == "cycle_position":
            self.root.after(0, self.cycle_position_mode)
            return
        if action_key == "cycle_input_mode":
            self.root.after(0, self.cycle_input_mode)
            return
        if action_key == "set_input_right_stick":
            self.root.after(0, lambda: self.set_input_mode("right_stick"))
            return
        if action_key == "set_input_left_stick":
            self.root.after(0, lambda: self.set_input_mode("left_stick"))
            return
        if action_key == "set_input_dpad":
            self.root.after(0, lambda: self.set_input_mode("dpad"))
            return
        if action_key == "next_custom_slot":
            self.root.after(0, self.cycle_custom_slot)
            return
        if action_key == "save_custom_location":
            self.root.after(0, self.capture_custom_location)
            return
        if action_key == "quit_app":
            self.root.after(0, self.stop)

    def cycle_position_mode(self):
        order = list(POSITION_LABELS.keys())
        index = order.index(self.settings["position_mode"])
        self.settings["position_mode"] = order[(index + 1) % len(order)]
        self.persist_settings(f"Position changed to {POSITION_LABELS[self.settings['position_mode']]}")

    def cycle_input_mode(self):
        order = list(INPUT_MODE_LABELS.keys())
        index = order.index(self.settings["input_mode"])
        self.settings["input_mode"] = order[(index + 1) % len(order)]
        self.persist_settings(f"Movement Lock input changed to {INPUT_MODE_LABELS[self.settings['input_mode']]}")

    def cycle_custom_slot(self):
        order = ["custom_1", "custom_2", "custom_3"]
        index = order.index(self.settings["custom_slot"])
        self.settings["custom_slot"] = order[(index + 1) % len(order)]
        self.persist_settings(f"Custom slot changed to {POSITION_LABELS[self.settings['custom_slot']]}")

    def left_click(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def perform_windows_remap(self, remap_name):
        remap_type, value = WINDOWS_REMAP_OPTIONS[remap_name]
        if remap_type == "mouse_click":
            down_flag, up_flag = {
                "left": (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
                "right": (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
                "middle": (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
            }[value]
            win32api.mouse_event(down_flag, 0, 0)
            win32api.mouse_event(up_flag, 0, 0)
            return
        if remap_type == "mouse_wheel":
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, value, 0)
            return
        if remap_type == "key_tap":
            win32api.keybd_event(value, 0, 0, 0)
            win32api.keybd_event(value, 0, win32con.KEYEVENTF_KEYUP, 0)

    def register_press(self, input_name, state):
        was_pressed = self.button_states.get(input_name, 0)
        self.button_states[input_name] = state
        if self.listening_for_input and state and not was_pressed:
            self.listening_for_input = False
            self.selected_input = input_name
            self.listen_status_label.config(text=f"{INPUT_LABELS[input_name]} selected")
            self.refresh_mapping_editor()
            self.refresh_mapping_grid()
            return
        if not state or was_pressed:
            return
        if input_name == "BTN_SELECT":
            self.toggle_overlay()
            return
        action_key = self.settings["input_actions"].get(input_name, "none")
        self.run_action(action_key, source_input=input_name)

    def process_controller_event(self, event):
        if event.code == "ABS_X":
            self.controller_state.lx = self.apply_deadzone(event.state / 32768.0)
            return
        if event.code == "ABS_Y":
            self.controller_state.ly = -self.apply_deadzone(event.state / 32768.0)
            return
        if event.code == "ABS_RX":
            self.controller_state.rx = self.apply_deadzone(event.state / 32768.0)
            return
        if event.code == "ABS_RY":
            self.controller_state.ry = -self.apply_deadzone(event.state / 32768.0)
            return
        if event.code == "ABS_Z":
            self.controller_state.lt = self.normalize_trigger(event.state)
            self.register_press("LT", 1 if self.controller_state.lt > 0.5 else 0)
            return
        if event.code == "ABS_RZ":
            self.controller_state.rt = self.normalize_trigger(event.state)
            self.register_press("RT", 1 if self.controller_state.rt > 0.5 else 0)
            return
        if event.code == "ABS_HAT0X":
            self.controller_state.dpad_x = int(event.state)
            self.register_press("DPAD_LEFT", 1 if event.state == -1 else 0)
            self.register_press("DPAD_RIGHT", 1 if event.state == 1 else 0)
            return
        if event.code == "ABS_HAT0Y":
            self.controller_state.dpad_y = int(event.state)
            self.register_press("DPAD_UP", 1 if event.state == -1 else 0)
            self.register_press("DPAD_DOWN", 1 if event.state == 1 else 0)
            return
        if event.code in SUPPORTED_INPUTS:
            self.register_press(event.code, int(event.state))

    def is_remapper_active(self):
        remapper_state = getattr(self, "_remapper_module_state", None)
        if remapper_state is None:
            return False
        remap_thread = getattr(remapper_state, "remap_thread", None)
        return bool(remap_thread and remap_thread.is_alive())

    def controller_loop(self):
        while self.running:
            try:
                events = get_gamepad()
                if events or self.controller_connected:
                    # Controller is connected or events exist
                    if not self.controller_connected:
                        self.controller_connected = True
                        self.controller_warning_shown = False
                        self.controller_disconnect_time = None
                        self.no_controller_overlay_shown = False  # Reset overlay flag when controller connects
                        self.root.after(0, self.update_controller_name_status)
                        # Hide overlay if it was shown due to no controller
                        self.root.after(0, self.hide_overlay_on_controller_connect)
                    for event in events:
                        if not self.running:
                            break
                        if self.is_remapper_active():
                            continue
                        self.process_controller_event(event)
                else:
                    # No gamepad events but keep checking
                    time.sleep(0.1)
            except Exception:
                # Controller disconnected or unavailable
                if self.controller_connected or not self.controller_warning_shown:
                    self.controller_connected = False
                    if self.controller_disconnect_time is None:
                        self.controller_disconnect_time = time.time()
                    else:
                        elapsed = time.time() - self.controller_disconnect_time
                        if elapsed >= self.controller_warning_timeout and not self.controller_warning_shown:
                            self.controller_warning_shown = True
                            self.root.after(0, lambda: self.set_status("⚠ No Controller Detected"))
                        elif elapsed < self.controller_warning_timeout:
                            self.root.after(0, lambda: self.set_status("Waiting for controller..."))
                time.sleep(0.4)

    def periodic_controller_check(self):
        """Check for controller name every 5 seconds"""
        if self.running:
            if self.controller_connected:
                self.update_controller_name_status()
            self.root.after(5000, self.periodic_controller_check)

    def detect_controller_name(self):
        """Attempt to detect the connected controller name"""
        try:
            import inputs
            # Try to get device information from the inputs library
            if hasattr(inputs, 'get_devices'):
                devices = inputs.get_devices()
                if devices:
                    for device in devices:
                        if hasattr(device, 'name'):
                            return device.name
                        elif hasattr(device, '_name'):
                            return device._name
                        # Return device string representation if available
                        device_str = str(device)
                        if device_str and device_str != '<GamePad ()>':
                            return device_str
            # Fallback: Try to get from gamepad event
            events = get_gamepad(timeout=0.1)
            if events and len(events) > 0:
                event = events[0]
                if hasattr(event, 'device'):
                    return event.device
        except Exception:
            pass
        return None

    def update_controller_name_status(self):
        """Update status with controller name if detected"""
        controller_name = self.detect_controller_name()
        if controller_name:
            self.controller_name = controller_name
            self.set_status(f"Controller: {controller_name}")
        else:
            self.set_status("Controller connected")

    def check_and_show_overlay_if_no_controller(self):
        """Automatically show overlay menu if no controller is detected at startup"""
        if not self.running or self.no_controller_overlay_shown:
            return
        if not self.controller_connected:
            self.no_controller_overlay_shown = True
            self.overlay_active = True
            self.overlay_target_y = 18
            self.overlay.deiconify()
            self.overlay.lift()

    def tick(self):
        if not self.running:
            return
        self.update_controller_movement()
        self.update_auto_hold()
        self.refresh_tester()
        self.root.after(16, self.tick)

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.holding_active:
            self.perform_auto_hold_up()
            self.holding_active = False
        self.overlay.withdraw()
        self.root.after(50, self.root.destroy)

    def run(self):
        self.root.mainloop()


def main():
    hide_console_window()
    app = ControllerMouseOverlayApp()
    app.run()


if __name__ == "__main__":
    main()
