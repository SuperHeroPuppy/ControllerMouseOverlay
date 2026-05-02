import functools
import os


CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CORE_DIR)
DEFAULT_SETTINGS_PATH = os.path.join(CORE_DIR, "settings.json")
CORE_MODULES_DIR = os.path.join(CORE_DIR, "modules")
OPTIONAL_MODULES_DIR = os.path.join(PROJECT_DIR, "modules")
COMMUNITY_MODULES_DIR = os.path.join(PROJECT_DIR, "community-modules")

APP_DIR = os.path.join(os.environ.get("APPDATA", os.getcwd()), "ControllerMouseOverlay")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
EXPORT_DIR = os.path.join(APP_DIR, "exports")
STYLE_EXPORT_DIR = os.path.join(EXPORT_DIR, "styles")
CONTROL_SHEET_EXPORT_DIR = os.path.join(EXPORT_DIR, "control_sheets")


@functools.lru_cache(maxsize=1)
def resolve_core_runtime_bundle():
    """(runtime_dir, core_py_path, info_json_path). Cached per process."""
    from core.module_registry import CORE_RUNTIME_SCRIPT, MODULE_INFO, find_core_runtime_dir

    runtime_dir = find_core_runtime_dir(CORE_MODULES_DIR)
    return (
        runtime_dir,
        os.path.join(runtime_dir, CORE_RUNTIME_SCRIPT),
        os.path.join(runtime_dir, MODULE_INFO),
    )


def get_core_runtime_dir():
    return resolve_core_runtime_bundle()[0]


def core_runtime_script_path():
    return resolve_core_runtime_bundle()[1]


def core_runtime_info_path():
    return resolve_core_runtime_bundle()[2]
