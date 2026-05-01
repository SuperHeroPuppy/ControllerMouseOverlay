import json
import os
import threading
import time
import tkinter as tk
from queue import Empty, Queue
from tkinter import messagebox, scrolledtext, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.app_config import APP_DIR
from core.controller_constants import COLORS

try:
    import pygame
except ImportError:
    pygame = None

try:
    import vgamepad as vg
except ImportError:
    vg = None


MODULE_DIR = os.path.dirname(__file__)
REMAPPER_APP_DIR = os.path.join(APP_DIR, "remapper")
MAPPING_FILE = os.path.join(REMAPPER_APP_DIR, "mapping.json")
DEADZONE = 0.15
POLL_DELAY = 0.005

DIGITAL_TARGETS = [
    "A",
    "B",
    "X",
    "Y",
    "LB",
    "RB",
    "BACK",
    "START",
    "LS",
    "RS",
    "DPAD_UP",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",
]

DIGITAL_TARGET_DESCRIPTIONS = {
    "A": "Xbox A (PS Cross / X)",
    "B": "Xbox B (PS Circle / O)",
    "X": "Xbox X (PS Square)",
    "Y": "Xbox Y (PS Triangle)",
    "LB": "Xbox LB (PS L1)",
    "RB": "Xbox RB (PS R1)",
    "BACK": "Xbox Back/View (PS Select)",
    "START": "Xbox Start/Menu (PS Start)",
    "LS": "Xbox Left Stick Click (PS L3)",
    "RS": "Xbox Right Stick Click (PS R3)",
    "DPAD_UP": "D-Pad Up",
    "DPAD_DOWN": "D-Pad Down",
    "DPAD_LEFT": "D-Pad Left",
    "DPAD_RIGHT": "D-Pad Right",
}

ANALOG_TARGETS = [
    ("LX", "Move left stick RIGHT"),
    ("LY", "Move left stick DOWN"),
    ("RX", "Move right stick RIGHT"),
    ("RY", "Move right stick DOWN"),
    ("LT", "Squeeze LEFT trigger"),
    ("RT", "Squeeze RIGHT trigger"),
]

DIGITAL_BUTTON_ENUM = {
    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
} if vg is not None else {}


class RemapperState:
    def __init__(self) -> None:
        self.mapping: Optional[Dict[str, Any]] = None
        self.joystick: Any = None
        self.controller_choices: List[Tuple[int, str]] = []

        self.remap_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.ui_queue: "Queue[Tuple[str, str]]" = Queue()

        self.initialized = False
        self.queue_pump_running = False
        self.calibration_active = False
        self.calibration_nav_action: Optional[str] = None

        self.frame: Optional[tk.Frame] = None
        self.controller_var: Optional[tk.StringVar] = None
        self.status_var: Optional[tk.StringVar] = None
        self.controller_combo: Any = None
        self.calibrate_btn: Any = None
        self.triggers_btn: Any = None
        self.start_btn: Any = None
        self.stop_btn: Any = None
        self.log_widget: Any = None
        self.mapping_label: Any = None
        self.dependency_label: Any = None
        self.calibration_info_label: Any = None
        self.calibration_step_label: Any = None
        self.calibration_progress: Any = None
        self.calibration_back_btn: Any = None
        self.calibration_skip_btn: Any = None

        self.log_lines: List[str] = []


def _state(app) -> RemapperState:
    current = getattr(app, "_remapper_module_state", None)
    if current is None:
        current = RemapperState()
        setattr(app, "_remapper_module_state", current)
    return current


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def signed_normalize_stick(value: float, deadzone: float = DEADZONE) -> float:
    if abs(value) < deadzone:
        return 0.0
    return clamp(value, -1.0, 1.0)


def normalize_trigger(value: float, mode: str) -> float:
    if mode == "zero_to_one":
        return clamp(value, 0.0, 1.0)
    return clamp((value + 1.0) / 2.0, 0.0, 1.0)


def _dependencies_ready() -> bool:
    return pygame is not None and vg is not None


def _dependency_message() -> str:
    missing = []
    if pygame is None:
        missing.append("pygame")
    if vg is None:
        missing.append("vgamepad")
    if not missing:
        return ""
    return "Missing dependency: " + ", ".join(missing)


def _consume_calibration_nav_action(app) -> Optional[str]:
    state = _state(app)
    action = state.calibration_nav_action
    state.calibration_nav_action = None
    return action


def _request_calibration_nav_action(app, action: str) -> None:
    state = _state(app)
    if not state.calibration_active:
        return
    state.calibration_nav_action = action


def _set_calibration_ui(app, active: bool, info: str = "", step_text: str = "", progress_value: int = 0, progress_total: int = 1, cooldown: bool = False) -> None:
    state = _state(app)

    if state.calibration_info_label is not None and state.calibration_info_label.winfo_exists():
        state.calibration_info_label.config(
            text=info,
            fg=COLORS["muted"] if cooldown else COLORS["text"],
        )

    if state.calibration_step_label is not None and state.calibration_step_label.winfo_exists():
        state.calibration_step_label.config(text=step_text)

    if state.calibration_progress is not None and state.calibration_progress.winfo_exists():
        safe_total = max(1, progress_total)
        state.calibration_progress.configure(maximum=safe_total)
        state.calibration_progress["value"] = max(0, min(progress_value, safe_total))

    nav_enabled = active and not cooldown
    nav_state = "normal" if nav_enabled else "disabled"
    if state.calibration_back_btn is not None and state.calibration_back_btn.winfo_exists():
        state.calibration_back_btn.configure(state=nav_state)
    if state.calibration_skip_btn is not None and state.calibration_skip_btn.winfo_exists():
        state.calibration_skip_btn.configure(state=nav_state)


def _run_cooldown(app, seconds: float) -> None:
    end_time = time.time() + seconds
    while time.time() < end_time:
        _safe_tick_ui(app)
        time.sleep(0.02)


def _init_pygame() -> None:
    if pygame is None:
        return
    if not pygame.get_init():
        pygame.init()
    if not pygame.joystick.get_init():
        pygame.joystick.init()


def _clear_pending_events() -> None:
    if pygame is not None:
        pygame.event.clear()


def _get_controller_list() -> List[Tuple[int, str]]:
    _init_pygame()
    if pygame is None:
        return []

    controllers: List[Tuple[int, str]] = []
    for idx in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(idx)
        js.init()
        controllers.append((idx, js.get_name()))
    return controllers


def _open_controller(index: int):
    _init_pygame()
    if pygame is None:
        return None
    js = pygame.joystick.Joystick(index)
    js.init()
    return js


def _wait_for_digital_input(joystick, tick_callback: Optional[Callable[[], None]] = None, app=None) -> Dict[str, Any]:
    pg = pygame
    if pg is None:
        raise RuntimeError("pygame is required for digital input capture")

    _clear_pending_events()

    while True:
        if tick_callback is not None:
            tick_callback()

        nav_action = _consume_calibration_nav_action(app) if app is not None else None
        if nav_action in {"back", "skip"}:
            return {"__nav__": nav_action}

        for event in pg.event.get():
            if event.type == pg.JOYBUTTONDOWN:
                return {"type": "button", "index": int(event.button)}

            if event.type == pg.JOYHATMOTION:
                x, y = event.value
                if x != 0 or y != 0:
                    return {
                        "type": "hat",
                        "index": int(event.hat),
                        "dir": [int(x), int(y)],
                    }

            if event.type == pg.JOYAXISMOTION:
                val = float(event.value)
                if abs(val) > 0.65:
                    return {
                        "type": "axis_as_button",
                        "index": int(event.axis),
                        "sign": 1 if val > 0 else -1,
                        "threshold": 0.5,
                    }

        time.sleep(POLL_DELAY)


def _wait_for_axis_input(
    joystick,
    is_trigger: bool,
    tick_callback: Optional[Callable[[], None]] = None,
    app=None,
) -> Dict[str, Any]:
    pg = pygame
    if pg is None:
        raise RuntimeError("pygame is required for axis input capture")

    _clear_pending_events()
    baseline = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]

    while True:
        if tick_callback is not None:
            tick_callback()

        nav_action = _consume_calibration_nav_action(app) if app is not None else None
        if nav_action in {"back", "skip"}:
            return {"__nav__": nav_action}

        for event in pg.event.get():
            if event.type == pg.JOYAXISMOTION and abs(float(event.value)) > 0.45:
                axis_index = int(event.axis)
                pressed_value = float(event.value)
                baseline_value = float(baseline[axis_index])

                mapping = {
                    "type": "axis",
                    "index": axis_index,
                    "invert": bool(pressed_value < 0),
                }

                if is_trigger:
                    mode = "neg1_to_pos1"
                    if 0.0 <= baseline_value <= 0.3 and pressed_value > baseline_value:
                        mode = "zero_to_one"
                    mapping["trigger_mode"] = mode
                    mapping["invert"] = False

                return mapping

        time.sleep(POLL_DELAY)


def _wait_for_trigger_input(joystick, tick_callback: Optional[Callable[[], None]] = None, app=None) -> Dict[str, Any]:
    pg = pygame
    if pg is None:
        raise RuntimeError("pygame is required for trigger input capture")

    _clear_pending_events()

    baseline_axes = [float(joystick.get_axis(i)) for i in range(joystick.get_numaxes())]
    baseline_buttons = [int(joystick.get_button(i)) for i in range(joystick.get_numbuttons())]

    while True:
        if tick_callback is not None:
            tick_callback()

        nav_action = _consume_calibration_nav_action(app) if app is not None else None
        if nav_action in {"back", "skip"}:
            return {"__nav__": nav_action}

        for event in pg.event.get():
            if event.type == pg.JOYBUTTONDOWN:
                return {
                    "type": "button_trigger",
                    "index": int(event.button),
                }

            if event.type == pg.JOYAXISMOTION:
                axis_index = int(event.axis)
                current_value = float(event.value)
                baseline_value = baseline_axes[axis_index]
                if abs(current_value - baseline_value) > 0.15:
                    mode = "neg1_to_pos1"
                    if -0.15 <= baseline_value <= 0.3 and current_value >= -0.15:
                        mode = "zero_to_one"
                    return {
                        "type": "axis",
                        "index": axis_index,
                        "invert": False,
                        "trigger_mode": mode,
                    }

        for axis_index in range(joystick.get_numaxes()):
            current_value = float(joystick.get_axis(axis_index))
            baseline_value = baseline_axes[axis_index]
            if abs(current_value - baseline_value) > 0.15:
                mode = "neg1_to_pos1"
                if -0.15 <= baseline_value <= 0.3 and current_value >= -0.15:
                    mode = "zero_to_one"
                return {
                    "type": "axis",
                    "index": axis_index,
                    "invert": False,
                    "trigger_mode": mode,
                }

        for button_index in range(joystick.get_numbuttons()):
            current_value = int(joystick.get_button(button_index))
            if current_value and current_value != baseline_buttons[button_index]:
                return {
                    "type": "button_trigger",
                    "index": button_index,
                }

        time.sleep(POLL_DELAY)


def _run_calibration(
    app,
    joystick,
    log_line: Callable[[str], None],
) -> Optional[Dict[str, Any]]:
    log_line("Calibration wizard started.")

    mapping: Dict[str, Any] = {
        "meta": {
            "controller_name": joystick.get_name(),
            "created_unix": time.time(),
        },
        "digital": {},
        "analog": {},
    }

    steps: List[Dict[str, str]] = []
    for target in DIGITAL_TARGETS:
        steps.append({
            "group": "digital",
            "target": target,
            "description": DIGITAL_TARGET_DESCRIPTIONS.get(target, target),
        })
    for target, prompt in ANALOG_TARGETS:
        steps.append({
            "group": "analog",
            "target": target,
            "description": prompt,
        })

    state = _state(app)
    state.calibration_active = True
    state.calibration_nav_action = None

    total = len(steps)
    index = 0

    while index < total:
        step = steps[index]
        target = step["target"]
        description = step["description"]
        group = step["group"]

        _set_calibration_ui(
            app,
            active=True,
            info="Target: " + description + "\nPress the control now.",
            step_text="Step " + str(index + 1) + " of " + str(total) + " - " + target,
            progress_value=index,
            progress_total=total,
        )

        if group == "digital":
            result = _wait_for_digital_input(joystick, tick_callback=lambda: _safe_tick_ui(app), app=app)
        else:
            is_trigger = target in ("LT", "RT")
            if is_trigger:
                result = _wait_for_trigger_input(joystick, tick_callback=lambda: _safe_tick_ui(app), app=app)
            else:
                result = _wait_for_axis_input(joystick, is_trigger, tick_callback=lambda: _safe_tick_ui(app), app=app)

        nav = result.get("__nav__") if isinstance(result, dict) else None
        if nav == "back":
            if index > 0:
                previous = steps[index - 1]
                previous_group = previous["group"]
                previous_target = previous["target"]
                mapping[previous_group].pop(previous_target, None)
                index -= 1
                log_line("Went back to remap " + previous_target)
            continue
        if nav == "skip":
            if group == "digital":
                mapping["digital"][target] = {"type": "none"}
            else:
                mapping["analog"][target] = {"type": "none"}
            log_line("Skipped " + target)
            index += 1
            continue

        mapping[group][target] = result
        log_line("Saved " + target + " -> " + str(result))
        _set_calibration_ui(
            app,
            active=True,
            info="Saved " + target + ". Cooldown...",
            step_text="Step " + str(index + 1) + " of " + str(total),
            progress_value=index + 1,
            progress_total=total,
            cooldown=True,
        )
        _run_cooldown(app, 0.5)
        index += 1

    state.calibration_active = False
    state.calibration_nav_action = None
    _set_calibration_ui(
        app,
        active=False,
        info="Calibration complete.",
        step_text="",
        progress_value=total,
        progress_total=total,
    )

    return mapping


def _run_trigger_recalibration(
    joystick,
    mapping: Dict[str, Any],
    prompt_step: Callable[[str, str], bool],
    log_line: Callable[[str], None],
    tick_callback: Optional[Callable[[], None]] = None,
) -> Optional[Dict[str, Any]]:
    log_line("Trigger-only recalibration started.")

    updated = json.loads(json.dumps(mapping))
    if "analog" not in updated:
        updated["analog"] = {}
    if "meta" not in updated:
        updated["meta"] = {}

    updated["meta"]["controller_name"] = joystick.get_name()
    updated["meta"]["updated_unix"] = time.time()

    for target, prompt in (("LT", "Squeeze LEFT trigger"), ("RT", "Squeeze RIGHT trigger")):
        title = "Remap " + target
        body = prompt + ", then click OK.\n\nAfter clicking OK, press that trigger once."
        if not prompt_step(title, body):
            log_line("Trigger-only recalibration canceled.")
            return None

        log_line("Waiting for trigger input for " + target + "...")
        updated["analog"][target] = _wait_for_trigger_input(joystick, tick_callback)
        log_line("Saved " + target + " -> " + str(updated["analog"][target]))

    return updated


def _save_mapping(mapping: Dict[str, Any]) -> None:
    os.makedirs(REMAPPER_APP_DIR, exist_ok=True)
    with open(MAPPING_FILE, "w", encoding="utf-8") as handle:
        json.dump(mapping, handle, indent=2)


def _load_mapping() -> Optional[Dict[str, Any]]:
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)

    return None


def _read_digital_source(joystick, source: Dict[str, Any]) -> bool:
    source_type = source.get("type")

    if source_type == "button":
        idx = int(source["index"])
        return bool(joystick.get_button(idx))

    if source_type == "hat":
        hat_idx = int(source["index"])
        target_dir = tuple(source["dir"])
        current = joystick.get_hat(hat_idx)
        return bool(current == target_dir)

    if source_type == "axis_as_button":
        axis_idx = int(source["index"])
        sign = int(source.get("sign", 1))
        threshold = float(source.get("threshold", 0.5))
        value = float(joystick.get_axis(axis_idx))
        return bool(value * sign > threshold)

    return False


def _read_analog_source(joystick, source: Dict[str, Any], target: str) -> float:
    if not source or source.get("type") == "none":
        return 0.0

    if source.get("type") == "button_trigger":
        button_idx = int(source["index"])
        return 1.0 if joystick.get_button(button_idx) else 0.0

    axis_idx = int(source["index"])
    value = float(joystick.get_axis(axis_idx))

    if target in ("LT", "RT"):
        mode = source.get("trigger_mode", "neg1_to_pos1")
        return normalize_trigger(value, mode)

    if bool(source.get("invert", False)):
        value = -value

    return signed_normalize_stick(value, DEADZONE)


def _apply_digital(gamepad, digital_state: Dict[str, bool]) -> None:
    for target, pressed in digital_state.items():
        button = DIGITAL_BUTTON_ENUM.get(target)
        if button is None:
            continue
        if pressed:
            gamepad.press_button(button=button)
        else:
            gamepad.release_button(button=button)


def _push_remapped_state_to_app(app, lx: float, ly: float, rx: float, ry: float, lt: float, rt: float, digital_state: Dict[str, bool]) -> None:
    controller_state = getattr(app, "controller_state", None)
    if controller_state is None:
        return

    controller_state.lx = float(lx)
    controller_state.ly = float(ly)
    controller_state.rx = float(rx)
    controller_state.ry = float(ry)
    controller_state.lt = float(lt)
    controller_state.rt = float(rt)

    dpad_x = 0
    dpad_y = 0
    if digital_state.get("DPAD_LEFT", False):
        dpad_x -= 1
    if digital_state.get("DPAD_RIGHT", False):
        dpad_x += 1
    if digital_state.get("DPAD_UP", False):
        dpad_y -= 1
    if digital_state.get("DPAD_DOWN", False):
        dpad_y += 1

    controller_state.dpad_x = dpad_x
    controller_state.dpad_y = dpad_y


def _safe_tick_ui(app) -> None:
    try:
        app.root.update_idletasks()
        app.root.update()
    except tk.TclError:
        pass


def _log(app, line: str) -> None:
    state = _state(app)
    timestamp = time.strftime("%H:%M:%S")
    rendered = "[" + timestamp + "] " + line
    state.log_lines.append(rendered)
    if len(state.log_lines) > 400:
        state.log_lines = state.log_lines[-400:]

    log_widget = state.log_widget
    if log_widget is None or not log_widget.winfo_exists():
        return

    log_widget.configure(state="normal")
    log_widget.insert("end", rendered + "\n")
    log_widget.see("end")
    log_widget.configure(state="disabled")


def _set_status(app, text: str) -> None:
    state = _state(app)
    if state.status_var is not None:
        state.status_var.set(text)


def _set_dependency_label(app) -> None:
    state = _state(app)
    if state.dependency_label is None or not state.dependency_label.winfo_exists():
        return

    message = _dependency_message()
    state.dependency_label.config(
        text=message,
        fg=COLORS["danger"],
    )


def _set_mapping_label(app) -> None:
    state = _state(app)
    if state.mapping_label is None or not state.mapping_label.winfo_exists():
        return

    if state.mapping is None:
        state.mapping_label.config(text="No mapping loaded")
        return

    controller_name = state.mapping.get("meta", {}).get("controller_name", "Unknown")
    text = "Loaded mapping for " + controller_name
    state.mapping_label.config(text=text)


def _set_action_buttons_enabled(app, remap_active: bool) -> None:
    state = _state(app)
    disabled = "disabled"
    normal = "normal"
    has_mapping = state.mapping is not None

    controls_locked = remap_active or state.calibration_active

    if state.calibrate_btn is not None and state.calibrate_btn.winfo_exists():
        has_mapping = state.mapping is not None
        calibrate_bg = COLORS["border"] if has_mapping else COLORS["success"]
        state.calibrate_btn.configure(
            text="Recalibrate" if has_mapping else "Calibrate",
            state=disabled if controls_locked else normal,
            bg=calibrate_bg,
            activebackground=calibrate_bg,
            fg=COLORS["text"],
            activeforeground=COLORS["text"],
            disabledforeground=COLORS["muted"],
        )

    if state.start_btn is not None and state.start_btn.winfo_exists():
        start_enabled = has_mapping and not controls_locked
        state.start_btn.configure(
            state=normal if start_enabled else disabled,
            bg=COLORS["accent_alt"] if start_enabled else COLORS["border"],
            activebackground=COLORS["accent"] if start_enabled else COLORS["border"],
            fg=COLORS["text"],
            activeforeground=COLORS["text"],
            disabledforeground=COLORS["muted"],
        )

    if state.stop_btn is not None and state.stop_btn.winfo_exists():
        state.stop_btn.configure(
            state=normal if remap_active else disabled,
            bg=COLORS["danger"] if remap_active else COLORS["border"],
            activebackground=COLORS["danger"] if remap_active else COLORS["border"],
            fg=COLORS["text"],
            activeforeground=COLORS["text"],
            disabledforeground=COLORS["muted"],
        )


def _refresh_controllers(app) -> None:
    state = _state(app)

    if pygame is None:
        state.controller_choices = []
        if state.controller_combo is not None and state.controller_combo.winfo_exists():
            state.controller_combo["values"] = ["pygame not installed"]
            state.controller_combo.current(0)
            state.controller_combo.configure(state="disabled")
        state.joystick = None
        _set_status(app, "Missing pygame")
        return

    try:
        choices = _get_controller_list()
    except Exception as exc:
        choices = []
        _log(app, "Controller refresh error: " + str(exc))

    state.controller_choices = choices
    combo = state.controller_combo

    if combo is None or not combo.winfo_exists():
        return

    if not choices:
        combo["values"] = ["No controllers detected"]
        combo.current(0)
        combo.configure(state="disabled")
        state.joystick = None
        _set_status(app, "No controller detected")
        return

    values = [str(idx) + ": " + name for idx, name in choices]
    combo.configure(state="readonly")
    combo["values"] = values
    combo.current(0)

    state.joystick = _open_controller(choices[0][0])
    _set_status(app, "Controller ready")


def _selected_joystick(app):
    state = _state(app)
    if not state.controller_choices:
        return None

    selected = 0
    combo = state.controller_combo
    if combo is not None and combo.winfo_exists():
        current = combo.current()
        if current >= 0:
            selected = current

    idx, name = state.controller_choices[selected]
    state.joystick = _open_controller(idx)
    _log(app, "Using controller: " + name)
    return state.joystick


def _prompt_step(app, title: str, body: str) -> bool:
    state = _state(app)
    parent = state.frame if state.frame is not None and state.frame.winfo_exists() else app.root
    return messagebox.askokcancel(title, body, parent=parent)


def _pump_ui_queue(app) -> None:
    state = _state(app)
    while True:
        try:
            kind, message = state.ui_queue.get_nowait()
        except Empty:
            break

        if kind == "log":
            _log(app, message)
        elif kind == "status":
            _set_status(app, message)
        elif kind == "stopped":
            _log(app, message)
            _set_status(app, "Ready")
            _set_action_buttons_enabled(app, remap_active=False)


def _run_queue_pump(app) -> None:
    state = _state(app)
    if state.queue_pump_running:
        return

    state.queue_pump_running = True

    def _tick():
        current_state = _state(app)
        if not current_state.queue_pump_running:
            return
        try:
            _pump_ui_queue(app)
        finally:
            try:
                app.root.after(80, _tick)
            except tk.TclError:
                current_state.queue_pump_running = False

    app.root.after(80, _tick)


def _start_page_refresh_loop(app, frame: tk.Frame) -> None:
    def _loop():
        if not getattr(app, "running", True):
            return
        if not frame.winfo_exists():
            return
        refresh(app)
        app.root.after(120, _loop)

    app.root.after(120, _loop)


def _mapping_has_required_axes(mapping: Dict[str, Any]) -> bool:
    analog = mapping.get("analog", {})
    for key in ("LX", "LY", "RX", "RY", "LT", "RT"):
        if key not in analog:
            return False
    return True


def _calibrate(app) -> None:
    state = _state(app)

    if state.remap_thread and state.remap_thread.is_alive():
        messagebox.showwarning("Remapper running", "Stop remapping before calibrating.", parent=app.root)
        return

    if pygame is None:
        messagebox.showerror("Missing dependency", "pygame is required for calibration.", parent=app.root)
        return

    joystick = _selected_joystick(app)
    if joystick is None:
        messagebox.showerror("No controller", "No controller detected.", parent=app.root)
        return

    if state.mapping is not None:
        confirmed = messagebox.askyesno(
            "Confirm Recalibration",
            "A mapping already exists. Recalibrating will overwrite the current mapping. Continue?",
            parent=app.root,
        )
        if not confirmed:
            return

    state.calibration_active = True
    _set_action_buttons_enabled(app, remap_active=False)
    _set_status(app, "Calibrating...")
    _log(app, "Calibration started.")

    new_mapping = _run_calibration(
        app=app,
        joystick=joystick,
        log_line=lambda line: _log(app, line),
    )

    if new_mapping is None:
        state.calibration_active = False
        _set_status(app, "Calibration canceled")
        _set_action_buttons_enabled(app, remap_active=False)
        return

    state.calibration_active = False
    state.mapping = new_mapping
    _save_mapping(new_mapping)
    _set_mapping_label(app)
    _set_action_buttons_enabled(app, remap_active=False)
    _set_status(app, "Calibration complete")
    _log(app, "Saved mapping to " + MAPPING_FILE)
    messagebox.showinfo("Done", "Calibration saved.", parent=app.root)


def _recalibrate_triggers(app) -> None:
    state = _state(app)

    if state.remap_thread and state.remap_thread.is_alive():
        messagebox.showwarning("Remapper running", "Stop remapping before remapping triggers.", parent=app.root)
        return

    if pygame is None:
        messagebox.showerror("Missing dependency", "pygame is required for calibration.", parent=app.root)
        return

    joystick = _selected_joystick(app)
    if joystick is None:
        messagebox.showerror("No controller", "No controller detected.", parent=app.root)
        return

    if state.mapping is None:
        messagebox.showwarning("No mapping", "No existing mapping found. Run full calibration first.", parent=app.root)
        return

    _set_status(app, "Recalibrating LT/RT...")
    updated_mapping = _run_trigger_recalibration(
        joystick=joystick,
        mapping=state.mapping,
        prompt_step=lambda title, body: _prompt_step(app, title, body),
        log_line=lambda line: _log(app, line),
        tick_callback=lambda: _safe_tick_ui(app),
    )

    if updated_mapping is None:
        _set_status(app, "Trigger remap canceled")
        return

    state.mapping = updated_mapping
    _save_mapping(updated_mapping)
    _set_mapping_label(app)
    _set_action_buttons_enabled(app, remap_active=False)
    _set_status(app, "LT/RT recalibration complete")
    _log(app, "Saved updated LT/RT mapping")
    messagebox.showinfo("Done", "Left and right triggers were remapped.", parent=app.root)


def _remap_loop(app, joystick, mapping: Dict[str, Any]) -> None:
    state = _state(app)
    pg = pygame
    vgp = vg
    if pg is None or vgp is None:
        state.ui_queue.put(("status", "Missing remapper dependencies"))
        return

    gamepad = vgp.VX360Gamepad()
    state.ui_queue.put(("log", "Virtual Xbox controller created."))
    start_was_pressed = False

    try:
        while not state.stop_event.is_set() and getattr(app, "running", True):
            pg.event.pump()

            digital_state: Dict[str, bool] = {}
            for target, source in mapping.get("digital", {}).items():
                digital_state[target] = _read_digital_source(joystick, source)

            start_is_pressed = bool(digital_state.get("START", False))
            if start_is_pressed and not start_was_pressed:
                try:
                    app.root.after(0, app.toggle_overlay)
                except Exception:
                    pass
            start_was_pressed = start_is_pressed

            analog = mapping.get("analog", {})
            lx = _read_analog_source(joystick, analog["LX"], "LX")
            ly = _read_analog_source(joystick, analog["LY"], "LY")
            rx = _read_analog_source(joystick, analog["RX"], "RX")
            ry = _read_analog_source(joystick, analog["RY"], "RY")
            lt = _read_analog_source(joystick, analog["LT"], "LT")
            rt = _read_analog_source(joystick, analog["RT"], "RT")

            # XInput uses negative Y as up.
            gamepad.left_joystick_float(x_value_float=lx, y_value_float=-ly)
            gamepad.right_joystick_float(x_value_float=rx, y_value_float=-ry)
            gamepad.left_trigger_float(value_float=lt)
            gamepad.right_trigger_float(value_float=rt)
            _apply_digital(gamepad, digital_state)
            gamepad.update()

            _push_remapped_state_to_app(app, lx, ly, rx, ry, lt, rt, digital_state)

            time.sleep(POLL_DELAY)

    except Exception as exc:
        state.ui_queue.put(("log", "Remapper error: " + str(exc)))
        state.ui_queue.put(("status", "Remapper error"))
    finally:
        try:
            gamepad.reset()
            gamepad.update()
        except Exception:
            pass
        state.ui_queue.put(("stopped", "Remapper stopped."))


def _start_remap(app) -> None:
    state = _state(app)

    if vg is None:
        messagebox.showerror(
            "Missing dependency",
            "vgamepad is not installed. Install vgamepad (and ViGEmBus) to start remapping.",
            parent=app.root,
        )
        return

    if pygame is None:
        messagebox.showerror("Missing dependency", "pygame is required to read controller input.", parent=app.root)
        return

    joystick = _selected_joystick(app)
    if joystick is None:
        messagebox.showerror("No controller", "No controller detected.", parent=app.root)
        return

    if state.mapping is None:
        messagebox.showwarning("No mapping", "No mapping found. Run calibration first.", parent=app.root)
        return

    if not _mapping_has_required_axes(state.mapping):
        messagebox.showwarning("Invalid mapping", "Mapping is missing required analog entries. Recalibrate.", parent=app.root)
        return

    if state.remap_thread and state.remap_thread.is_alive():
        return

    state.stop_event.clear()
    state.remap_thread = threading.Thread(
        target=_remap_loop,
        args=(app, joystick, state.mapping),
        daemon=True,
    )
    state.remap_thread.start()

    _set_action_buttons_enabled(app, remap_active=True)
    _set_status(app, "Remapping active")
    _log(app, "Remapper started.")


def _stop_remap(app) -> None:
    state = _state(app)
    state.stop_event.set()
    _set_status(app, "Stopping remapper...")


def build_page(self, parent):
    state = _state(self)

    frame = tk.Frame(parent, bg=COLORS["bg"])
    state.frame = frame

    left = tk.Frame(frame, bg=COLORS["bg"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    right = tk.Frame(frame, bg=COLORS["bg"])
    right.pack(side="left", fill="both", expand=True)

    control_card = tk.Frame(left, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    control_card.pack(fill="both", expand=True)

    tk.Label(control_card, text="Controller Remapper", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(
        control_card,
        text="Calibrate a physical controller layout and output remapped input to a virtual Xbox 360 controller.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=470,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    state.controller_var = tk.StringVar()
    state.status_var = tk.StringVar(value="Ready")

    row = tk.Frame(control_card, bg=COLORS["panel"])
    row.pack(fill="x")
    tk.Label(row, text="Controller", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(side="left")

    state.controller_combo = ttk.Combobox(row, textvariable=state.controller_var, state="readonly", width=44)
    state.controller_combo.pack(side="left", padx=(10, 8), fill="x", expand=True)

    ttk.Button(row, text="Refresh", command=lambda: _refresh_controllers(self)).pack(side="left")

    state.mapping_label = tk.Label(control_card, text="", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=470, justify="left")
    state.mapping_label.pack(anchor="w", pady=(10, 0))

    state.dependency_label = tk.Label(control_card, text="", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=470, justify="left")
    state.dependency_label.pack(anchor="w", pady=(4, 0))

    buttons = tk.Frame(control_card, bg=COLORS["panel"])
    buttons.pack(fill="x", pady=(14, 0))

    state.calibrate_btn = tk.Button(
        buttons,
        text="Calibrate",
        command=lambda: _calibrate(self),
        relief="flat",
        bd=0,
        padx=12,
        pady=9,
        bg=COLORS["success"],
        fg=COLORS["text"],
        activebackground=COLORS["success"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    )
    state.calibrate_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

    run_row = tk.Frame(control_card, bg=COLORS["panel"])
    run_row.pack(fill="x", pady=(10, 0))

    state.start_btn = tk.Button(
        run_row,
        text="Start Remap",
        command=lambda: _start_remap(self),
        relief="flat",
        bd=0,
        padx=12,
        pady=9,
        bg=COLORS["border"],
        fg=COLORS["text"],
        activebackground=COLORS["border"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
        state="disabled",
    )
    state.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

    state.stop_btn = tk.Button(
        run_row,
        text="Stop Remap",
        command=lambda: _stop_remap(self),
        relief="flat",
        bd=0,
        padx=12,
        pady=9,
        bg=COLORS["border"],
        fg=COLORS["text"],
        activebackground=COLORS["border"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
        state="disabled",
    )
    state.stop_btn.pack(side="left", fill="x", expand=True)

    status_row = tk.Frame(control_card, bg=COLORS["panel"])
    status_row.pack(fill="x", pady=(10, 0))
    tk.Label(status_row, text="Status", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(side="left")
    tk.Label(status_row, textvariable=state.status_var, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="right")

    calibration_card = tk.Frame(control_card, bg=COLORS["panel_alt"], padx=10, pady=10, highlightthickness=1, highlightbackground=COLORS["border"])
    calibration_card.pack(fill="x", pady=(10, 0))

    state.calibration_info_label = tk.Label(
        calibration_card,
        text="Calibration instructions will appear here.",
        bg=COLORS["panel_alt"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=440,
        justify="left",
    )
    state.calibration_info_label.pack(anchor="w")

    state.calibration_step_label = tk.Label(
        calibration_card,
        text="",
        bg=COLORS["panel_alt"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
    )
    state.calibration_step_label.pack(anchor="w", pady=(6, 0))

    state.calibration_progress = ttk.Progressbar(calibration_card, orient="horizontal", mode="determinate", maximum=1)
    state.calibration_progress.pack(fill="x", pady=(6, 0))

    nav_row = tk.Frame(calibration_card, bg=COLORS["panel_alt"])
    nav_row.pack(fill="x", pady=(8, 0))

    state.calibration_back_btn = tk.Button(
        nav_row,
        text="I made a mistake",
        command=lambda: _request_calibration_nav_action(self, "back"),
        relief="flat",
        bd=0,
        padx=10,
        pady=7,
        bg=COLORS["card"],
        fg=COLORS["text"],
        activebackground=COLORS["card_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI", 9),
        cursor="hand2",
        state="disabled",
    )
    state.calibration_back_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

    state.calibration_skip_btn = tk.Button(
        nav_row,
        text="I don't have this button",
        command=lambda: _request_calibration_nav_action(self, "skip"),
        relief="flat",
        bd=0,
        padx=10,
        pady=7,
        bg=COLORS["card"],
        fg=COLORS["text"],
        activebackground=COLORS["card_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI", 9),
        cursor="hand2",
        state="disabled",
    )
    state.calibration_skip_btn.pack(side="left", fill="x", expand=True)

    log_card = tk.Frame(right, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    log_card.pack(fill="both", expand=True)
    tk.Label(log_card, text="Session Log", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(
        log_card,
        text=(
            "Install notes: pip install pygame vgamepad. "
            "vgamepad also needs the ViGEmBus driver on Windows."
        ),
        bg=COLORS["card"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=360,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    state.log_widget = scrolledtext.ScrolledText(
        log_card,
        wrap="word",
        height=24,
        state="disabled",
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        bd=0,
        padx=10,
        pady=10,
        font=("Consolas", 9),
    )
    state.log_widget.pack(fill="both", expand=True)

    if not state.initialized:
        state.mapping = _load_mapping()
        state.initialized = True
        _log(self, "Remapper module initialized.")
        _log(self, "Mapping file path: " + MAPPING_FILE)
        if state.mapping is None:
            _log(self, "No mapping found yet. Run calibration first.")
        else:
            controller_name = state.mapping.get("meta", {}).get("controller_name", "unknown")
            _log(self, "Loaded existing mapping for: " + controller_name)

    for line in state.log_lines:
        state.log_widget.configure(state="normal")
        state.log_widget.insert("end", line + "\n")
        state.log_widget.configure(state="disabled")
    state.log_widget.see("end")

    _refresh_controllers(self)
    _set_dependency_label(self)
    _set_mapping_label(self)
    _set_action_buttons_enabled(self, remap_active=bool(state.remap_thread and state.remap_thread.is_alive()))
    _run_queue_pump(self)
    _start_page_refresh_loop(self, frame)

    return frame


def refresh(self):
    state = _state(self)
    _pump_ui_queue(self)
    _set_dependency_label(self)
    _set_mapping_label(self)

    remap_active = bool(state.remap_thread and state.remap_thread.is_alive())
    _set_action_buttons_enabled(self, remap_active=remap_active)

    if remap_active and state.status_var is not None and not state.status_var.get():
        state.status_var.set("Remapping active")