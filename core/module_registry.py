import importlib.util
import json
import os
import re


MODULE_SCRIPT = "module.py"
MODULE_INFO = "info.json"
CORE_RUNTIME_SCRIPT = "core.py"
MODULE_FOLDER_PATTERN = re.compile(r"^\d+\.\d+\.\d+_[A-Za-z0-9_]+(?:_core)?$")


def _folder_semver_key(entry):
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)_", entry)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def _has_standard_module_script(module_dir):
    return os.path.isfile(os.path.join(module_dir, MODULE_SCRIPT))


class ModuleLoadError(Exception):
    pass


def read_module_info(module_dir):
    info_path = os.path.join(module_dir, MODULE_INFO)
    if not os.path.exists(info_path):
        raise ModuleLoadError(f"Missing {MODULE_INFO}")
    try:
        with open(info_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModuleLoadError(f"Invalid {MODULE_INFO}: {exc}") from exc


def find_core_runtime_dir(modules_dir):
    """Resolve the bundled core app runtime folder (core.py, no module.py, registry_name core).

    If several match (e.g. side-by-side upgrades), the highest major.minor.patch folder prefix wins.
    """
    if not os.path.isdir(modules_dir):
        raise ModuleLoadError(f"Module folder not found: {modules_dir}")
    candidates = []
    for entry in os.listdir(modules_dir):
        module_dir = os.path.join(modules_dir, entry)
        if not os.path.isdir(module_dir) or not MODULE_FOLDER_PATTERN.match(entry):
            continue
        if _has_standard_module_script(module_dir):
            continue
        if not os.path.isfile(os.path.join(module_dir, CORE_RUNTIME_SCRIPT)):
            continue
        try:
            info = read_module_info(module_dir)
        except ModuleLoadError:
            continue
        if info.get("registry_name") != "core":
            continue
        candidates.append((_folder_semver_key(entry), module_dir))
    if not candidates:
        raise ModuleLoadError(
            "No core runtime folder found under core/modules (need a versioned folder with "
            f"{CORE_RUNTIME_SCRIPT}, {MODULE_INFO} registry_name 'core', and no {MODULE_SCRIPT})"
        )
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def find_module_dir(modules_dir, registry_name):
    if not os.path.isdir(modules_dir):
        raise ModuleLoadError(f"Module folder not found: {modules_dir}")
    for entry in sorted(os.listdir(modules_dir)):
        module_dir = os.path.join(modules_dir, entry)
        if not os.path.isdir(module_dir) or not MODULE_FOLDER_PATTERN.match(entry):
            continue
        if not _has_standard_module_script(module_dir):
            continue
        try:
            info = read_module_info(module_dir)
        except ModuleLoadError:
            continue
        if info.get("registry_name") == registry_name:
            return module_dir, info
    raise ModuleLoadError(f"Module not registered: {registry_name}")


def discover_registered_modules(modules_dir):
    modules = []
    if not os.path.isdir(modules_dir):
        return modules
    for entry in sorted(os.listdir(modules_dir)):
        module_dir = os.path.join(modules_dir, entry)
        if not os.path.isdir(module_dir) or not MODULE_FOLDER_PATTERN.match(entry):
            continue
        if not _has_standard_module_script(module_dir):
            continue
        try:
            info = read_module_info(module_dir)
        except ModuleLoadError as exc:
            info = {
                "display_name": entry,
                "registry_name": entry,
                "version": "Unknown",
                "description": f"Could not read module metadata: {exc}",
                "libraries": [],
                "creators": [],
            }
        modules.append({"folder": entry, "path": module_dir, "info": info})
    return modules


def load_registered_module(modules_dir, registry_name):
    module_dir, info = find_module_dir(modules_dir, registry_name)
    script_path = os.path.join(module_dir, MODULE_SCRIPT)
    if not os.path.exists(script_path):
        raise ModuleLoadError(f"Missing {MODULE_SCRIPT}")

    import_name = f"registered_module_{registry_name.replace('.', '_').replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(import_name, script_path)
    if spec is None or spec.loader is None:
        raise ModuleLoadError(f"Cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ModuleLoadError(f"Module failed to load: {exc}") from exc
    return module, info
