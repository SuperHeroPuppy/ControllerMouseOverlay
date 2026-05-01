import os
import sys


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(PROJECT_DIR, "core")
CORE_APP_PATH = os.path.join(CORE_DIR, "app.py")
CORE_INFO_PATH = os.path.join(CORE_DIR, "info.json")


def main():
    missing = [
        path
        for path in (CORE_DIR, CORE_APP_PATH, CORE_INFO_PATH)
        if not os.path.exists(path)
    ]
    if missing:
        print("Controller Mouse Overlay cannot start because the required core module is missing:")
        for path in missing:
            print(f"  - {path}")
        return 1

    if PROJECT_DIR not in sys.path:
        sys.path.insert(0, PROJECT_DIR)

    from core.app import main as run_app

    run_app()
    return 0

    
if __name__ == "__main__":
    raise SystemExit(main())
