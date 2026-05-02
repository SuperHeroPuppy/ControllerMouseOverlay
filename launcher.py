import importlib.util
import os
import sys


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(PROJECT_DIR, "core")


def main():
    if PROJECT_DIR not in sys.path:
        sys.path.insert(0, PROJECT_DIR)

    try:
        from core.module_registry import ModuleLoadError
        from core.app_config import core_runtime_info_path, core_runtime_script_path

        script_path = core_runtime_script_path()
        info_path = core_runtime_info_path()
    except ModuleLoadError as exc:
        print("Controller Mouse Overlay cannot resolve the core runtime bundle:")
        print(f"  {exc}")
        return 1

    missing = [path for path in (CORE_DIR, script_path, info_path) if not os.path.exists(path)]
    if missing:
        print("Controller Mouse Overlay cannot start because the required core module is missing:")
        for path in missing:
            print(f"  - {path}")
        return 1
    import_name = "controller_mouse_overlay_core_runtime"
    spec = importlib.util.spec_from_file_location(import_name, script_path)
    if spec is None or spec.loader is None:
        print(f"Cannot load core runtime from {script_path}")
        return 1

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"Core runtime failed to load: {exc}")
        return 1

    run = getattr(module, "main", None)
    if run is None:
        print("Core runtime module has no main()")
        return 1

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
