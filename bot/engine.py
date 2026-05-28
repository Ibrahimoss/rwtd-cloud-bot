"""
YAML-driven state machine for game automation.

States are defined declaratively:

    states:
      main_menu:
        detect: templates/main_menu_anchor.png
        actions:
          - tap: [540, 1820]
          - wait: 2
        transitions:
          - if_visible: templates/in_battle.png
            to: battle
      battle:
        detect: templates/in_battle.png
        actions:
          - wait: 10
        transitions:
          - if_visible: templates/victory.png
            to: collect_reward

The runner takes a screenshot, finds which state matches, runs its actions,
then checks transitions. If no state matches, dumps a debug screenshot.
"""

import time
import yaml
from pathlib import Path
from loguru import logger

from airtest.core.api import touch, swipe, snapshot, Template, exists


class StateMachineRunner:
    def __init__(self, state_file, device, poll_interval=3.0, on_state_change=None, notifier=None):
        self.state_file = Path(state_file)
        self.device = device
        self.poll_interval = poll_interval
        self.on_state_change = on_state_change or (lambda s: None)
        self.notifier = notifier
        self.config = self._load_config()
        self.current_state = self.config.get("initial_state")
        self.template_root = self.state_file.parent

    def _load_config(self):
        with open(self.state_file) as f:
            return yaml.safe_load(f)

    def _resolve_template(self, path):
        # Allow relative paths in YAML, resolved against the state file location
        return str((self.template_root / path).resolve())

    def _is_visible(self, template_path, threshold=0.85):
        try:
            return exists(Template(self._resolve_template(template_path), threshold=threshold))
        except Exception as e:
            logger.warning(f"Template check failed for {template_path}: {e}")
            return False

    def _run_actions(self, actions):
        for action in actions or []:
            for verb, arg in action.items():
                if verb == "tap":
                    touch(arg)
                elif verb == "swipe":
                    swipe(arg[0], arg[1])
                elif verb == "wait":
                    time.sleep(float(arg))
                elif verb == "log":
                    logger.info(str(arg))
                else:
                    logger.warning(f"Unknown action: {verb}")

    def _detect_state(self):
        """Find which defined state's anchor template is currently on screen."""
        for name, spec in self.config["states"].items():
            if self._is_visible(spec["detect"]):
                return name
        return None

    def _save_debug_snapshot(self):
        ts = int(time.time())
        path = f"/app/screenshots/unknown_{ts}.png"
        snapshot(filename=path)
        logger.warning(f"Unknown screen state - saved {path}")
        return path

    def step(self):
        # 1. If we have a current state, run its actions
        if self.current_state and self.current_state in self.config["states"]:
            spec = self.config["states"][self.current_state]
            self._run_actions(spec.get("actions"))

            # 2. Check transitions
            for transition in spec.get("transitions", []):
                cond = transition.get("if_visible")
                target = transition.get("to")
                if cond and self._is_visible(cond):
                    logger.info(f"Transition: {self.current_state} -> {target}")
                    self.current_state = target
                    self.on_state_change(target)
                    return

        # 3. Re-detect from scratch (recovery)
        detected = self._detect_state()
        if detected and detected != self.current_state:
            logger.info(f"Detected state: {detected}")
            self.current_state = detected
            self.on_state_change(detected)
        elif not detected:
            self._save_debug_snapshot()

    def run_forever(self):
        logger.info(f"State machine starting at: {self.current_state}")
        while True:
            try:
                self.step()
            except Exception:
                logger.exception("Step failed")
                self._save_debug_snapshot()
            time.sleep(self.poll_interval)
