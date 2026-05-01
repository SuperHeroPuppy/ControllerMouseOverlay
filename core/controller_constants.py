import json

import win32con

from core.app_config import DEFAULT_SETTINGS_PATH


COLORS = {
    "bg": "#0b1020",
    "panel": "#11182b",
    "panel_alt": "#0d1425",
    "card": "#161f34",
    "card_alt": "#1c2740",
    "border": "#243252",
    "text": "#edf2ff",
    "muted": "#9babcc",
    "accent": "#5eead4",
    "accent_alt": "#60a5fa",
    "danger": "#fb7185",
    "success": "#34d399",
}

SUPPORTED_INPUTS = [
    "BTN_SELECT",
    "BTN_START",
    "BTN_SOUTH",
    "BTN_EAST",
    "BTN_WEST",
    "BTN_NORTH",
    "BTN_TL",
    "BTN_TR",
    "BTN_THUMBL",
    "BTN_THUMBR",
    "DPAD_UP",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",
    "LT",
    "RT",
]

INPUT_LABELS = {
    "BTN_SELECT": "View",
    "BTN_START": "Menu",
    "BTN_SOUTH": "A",
    "BTN_EAST": "B",
    "BTN_WEST": "X",
    "BTN_NORTH": "Y",
    "BTN_TL": "LB",
    "BTN_TR": "RB",
    "BTN_THUMBL": "LS",
    "BTN_THUMBR": "RS",
    "DPAD_UP": "D-Pad Up",
    "DPAD_DOWN": "D-Pad Down",
    "DPAD_LEFT": "D-Pad Left",
    "DPAD_RIGHT": "D-Pad Right",
    "LT": "Left Trigger",
    "RT": "Right Trigger",
}

SHORT_INPUT_LABELS = {
    "BTN_SELECT": "View",
    "BTN_START": "Menu",
    "BTN_SOUTH": "A",
    "BTN_EAST": "B",
    "BTN_WEST": "X",
    "BTN_NORTH": "Y",
    "BTN_TL": "LB",
    "BTN_TR": "RB",
    "BTN_THUMBL": "LS",
    "BTN_THUMBR": "RS",
    "DPAD_UP": "Up",
    "DPAD_DOWN": "Down",
    "DPAD_LEFT": "Left",
    "DPAD_RIGHT": "Right",
    "LT": "LT",
    "RT": "RT",
}

INPUT_MODE_LABELS = {
    "right_stick": "Right Stick",
    "left_stick": "Left Stick",
    "dpad": "D-Pad",
}

POSITION_LABELS = {
    "center": "Center",
    "top_left": "Top Left",
    "top_right": "Top Right",
    "bottom_left": "Bottom Left",
    "bottom_right": "Bottom Right",
    "custom_1": "Custom 1",
    "custom_2": "Custom 2",
    "custom_3": "Custom 3",
}

AUTO_HOLD_OPTIONS = {
    "Right Mouse": ("mouse", "right"),
    "Left Mouse": ("mouse", "left"),
    "Middle Mouse": ("mouse", "middle"),
    "Space": ("key", 0x20),
    "Left Shift": ("key", win32con.VK_LSHIFT),
    "Left Ctrl": ("key", win32con.VK_LCONTROL),
    "Left Alt": ("key", win32con.VK_LMENU),
    "E": ("key", 0x45),
    "F": ("key", 0x46),
    "Q": ("key", 0x51),
    "R": ("key", 0x52),
}

WINDOWS_REMAP_OPTIONS = {
    "Left Click": ("mouse_click", "left"),
    "Right Click": ("mouse_click", "right"),
    "Middle Click": ("mouse_click", "middle"),
    "Scroll Up": ("mouse_wheel", 120),
    "Scroll Down": ("mouse_wheel", -120),
    "Space": ("key_tap", 0x20),
    "Enter": ("key_tap", win32con.VK_RETURN),
    "Tab": ("key_tap", win32con.VK_TAB),
    "Escape": ("key_tap", win32con.VK_ESCAPE),
    "Backspace": ("key_tap", win32con.VK_BACK),
    "Left Shift": ("key_tap", win32con.VK_LSHIFT),
    "Left Ctrl": ("key_tap", win32con.VK_LCONTROL),
    "Left Alt": ("key_tap", win32con.VK_LMENU),
    "Up Arrow": ("key_tap", win32con.VK_UP),
    "Down Arrow": ("key_tap", win32con.VK_DOWN),
    "Left Arrow": ("key_tap", win32con.VK_LEFT),
    "Right Arrow": ("key_tap", win32con.VK_RIGHT),
    "A": ("key_tap", 0x41),
    "B": ("key_tap", 0x42),
    "C": ("key_tap", 0x43),
    "D": ("key_tap", 0x44),
    "E": ("key_tap", 0x45),
    "F": ("key_tap", 0x46),
    "G": ("key_tap", 0x47),
    "H": ("key_tap", 0x48),
    "I": ("key_tap", 0x49),
    "J": ("key_tap", 0x4A),
    "K": ("key_tap", 0x4B),
    "L": ("key_tap", 0x4C),
    "M": ("key_tap", 0x4D),
    "N": ("key_tap", 0x4E),
    "O": ("key_tap", 0x4F),
    "P": ("key_tap", 0x50),
    "Q": ("key_tap", 0x51),
    "R": ("key_tap", 0x52),
    "S": ("key_tap", 0x53),
    "T": ("key_tap", 0x54),
    "U": ("key_tap", 0x55),
    "V": ("key_tap", 0x56),
    "W": ("key_tap", 0x57),
    "X": ("key_tap", 0x58),
    "Y": ("key_tap", 0x59),
    "Z": ("key_tap", 0x5A),
    "0": ("key_tap", 0x30),
    "1": ("key_tap", 0x31),
    "2": ("key_tap", 0x32),
    "3": ("key_tap", 0x33),
    "4": ("key_tap", 0x34),
    "5": ("key_tap", 0x35),
    "6": ("key_tap", 0x36),
    "7": ("key_tap", 0x37),
    "8": ("key_tap", 0x38),
    "9": ("key_tap", 0x39),
}

ACTION_DEFINITIONS = {
    "none": ("No Action", "Leaves this input unused."),
    "toggle_overlay": ("Toggle Overlay", "Open or close the overlay."),
    "ui_click": ("UI Click", "Clicks the overlay at the current cursor position."),
    "ui_scroll_up": ("UI Scroll Up", "Scrolls the overlay upward while it is open."),
    "ui_scroll_down": ("UI Scroll Down", "Scrolls the overlay downward while it is open."),
    "windows_remap": ("Windows Remap", "Sends a keyboard or mouse output selected below."),
    "toggle_movement": ("Toggle Movement Lock", "Turns movement lock on or off."),
    "enable_movement": ("Enable Movement Lock", "Forces movement lock on."),
    "disable_movement": ("Disable Movement Lock", "Forces movement lock off."),
    "toggle_control_windows": ("Toggle Control Windows", "Turns free mouse control on or off."),
    "enable_control_windows": ("Enable Control Windows", "Forces free mouse control on."),
    "disable_control_windows": ("Disable Control Windows", "Forces free mouse control off."),
    "toggle_auto_hold": ("Toggle Auto Hold", "Turns auto hold on or off."),
    "enable_auto_hold": ("Enable Auto Hold", "Forces auto hold on."),
    "disable_auto_hold": ("Disable Auto Hold", "Forces auto hold off."),
    "toggle_auto_enable_movement": ("Toggle Auto Enable", "Turns auto-enable movement lock on or off."),
    "enable_auto_enable_movement": ("Enable Auto Enable", "Forces auto-enable movement lock on."),
    "disable_auto_enable_movement": ("Disable Auto Enable", "Forces auto-enable movement lock off."),
    "cycle_position": ("Cycle Position", "Moves to the next lock position."),
    "cycle_input_mode": ("Cycle Input Mode", "Switches right stick, left stick, or D-pad control."),
    "set_input_right_stick": ("Use Right Stick", "Sets movement lock to the right stick."),
    "set_input_left_stick": ("Use Left Stick", "Sets movement lock to the left stick."),
    "set_input_dpad": ("Use D-Pad", "Sets movement lock to the D-pad."),
    "next_custom_slot": ("Next Custom Slot", "Switches between Custom 1, 2, and 3."),
    "save_custom_location": ("Save Custom Location", "Stores the current cursor position in the active custom slot."),
    "quit_app": ("Quit App", "Closes the overlay application."),
}

ACTION_KEYS = list(ACTION_DEFINITIONS.keys())


def _load_default_settings_file():
    with open(DEFAULT_SETTINGS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_default_settings():
    settings = _load_default_settings_file()
    settings.setdefault("input_actions", {})
    settings.setdefault("input_remaps", {})
    settings.setdefault("style", {})
    for input_name in SUPPORTED_INPUTS:
        settings["input_actions"].setdefault(input_name, "none")
        settings["input_remaps"].setdefault(input_name, "Right Click")
    for key, value in COLORS.items():
        settings["style"].setdefault(key, value)
    return settings


DEFAULT_SETTINGS = load_default_settings()
