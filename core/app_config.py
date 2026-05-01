import os


CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CORE_DIR)
CORE_INFO_PATH = os.path.join(CORE_DIR, "info.json")
DEFAULT_SETTINGS_PATH = os.path.join(CORE_DIR, "settings.json")
CORE_MODULES_DIR = os.path.join(CORE_DIR, "modules")
OPTIONAL_MODULES_DIR = os.path.join(PROJECT_DIR, "modules")

APP_DIR = os.path.join(os.environ.get("APPDATA", os.getcwd()), "ControllerMouseOverlay")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
EXPORT_DIR = os.path.join(APP_DIR, "exports")
STYLE_EXPORT_DIR = os.path.join(EXPORT_DIR, "styles")
CONTROL_SHEET_EXPORT_DIR = os.path.join(EXPORT_DIR, "control_sheets")
