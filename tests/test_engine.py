"""
Tests for the YAML state machine engine.

- Smoke tests: YAML parsing and required fields.
- Engine tests: state detection, actions, transitions, and recovery — all
  with mocked Airtest so no Android device is needed.
"""

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest
import yaml


# ---------------------------------------------------------------------------
# Smoke tests (existing)
# ---------------------------------------------------------------------------

def test_rwtd_yaml_loads():
    state_file = Path("bot/states/rwtd.yaml")
    assert state_file.exists()
    config = yaml.safe_load(state_file.read_text())
    assert "states" in config
    assert "initial_state" in config


def test_yaml_states_have_required_fields(tmp_path):
    sample = textwrap.dedent("""
        initial_state: a
        states:
          a:
            detect: foo.png
            actions:
              - tap: [10, 20]
            transitions:
              - if_visible: bar.png
                to: b
          b:
            detect: bar.png
            actions: []
            transitions: []
    """)
    p = tmp_path / "test.yaml"
    p.write_text(sample)
    config = yaml.safe_load(p.read_text())
    for name, spec in config["states"].items():
        assert "detect" in spec, f"State {name} missing 'detect'"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_YAML = textwrap.dedent("""\
    initial_state: menu
    states:
      menu:
        detect: menu.png
        actions:
          - log: "on menu"
          - tap: [100, 200]
          - wait: 0.01
        transitions:
          - if_visible: battle.png
            to: battle
      battle:
        detect: battle.png
        actions:
          - log: "in battle"
          - swipe: [[100, 200], [300, 400]]
          - wait: 0.01
        transitions:
          - if_visible: victory.png
            to: victory
      victory:
        detect: victory.png
        actions:
          - log: "victory"
          - tap: [360, 1700]
        transitions:
          - if_visible: menu.png
            to: menu
""")


@pytest.fixture()
def state_file(tmp_path):
    p = tmp_path / "test.yaml"
    p.write_text(SAMPLE_YAML)
    return p


@pytest.fixture()
def airtest_mocks():
    """Patch all Airtest symbols used by engine.py."""
    with (
        patch("bot.engine.touch") as m_touch,
        patch("bot.engine.swipe") as m_swipe,
        patch("bot.engine.snapshot") as m_snapshot,
        patch("bot.engine.exists") as m_exists,
        patch("bot.engine.Template") as m_template,
    ):
        m_template.side_effect = lambda path, **kw: path
        yield {
            "touch": m_touch,
            "swipe": m_swipe,
            "snapshot": m_snapshot,
            "exists": m_exists,
            "template": m_template,
        }


def make_runner(state_file, airtest_mocks, **kwargs):
    from bot.engine import StateMachineRunner
    return StateMachineRunner(state_file, device=MagicMock(), **kwargs)


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

class TestDetectState:
    def test_detects_matching_state(self, state_file, airtest_mocks):
        airtest_mocks["exists"].side_effect = lambda tpl, **kw: "menu.png" in str(tpl)
        runner = make_runner(state_file, airtest_mocks)
        assert runner._detect_state() == "menu"

    def test_returns_none_when_nothing_matches(self, state_file, airtest_mocks):
        airtest_mocks["exists"].return_value = False
        runner = make_runner(state_file, airtest_mocks)
        assert runner._detect_state() is None


class TestRunActions:
    def test_tap_action(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        runner._run_actions([{"tap": [100, 200]}])
        airtest_mocks["touch"].assert_called_once_with([100, 200])

    def test_swipe_action(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        runner._run_actions([{"swipe": [[100, 200], [300, 400]]}])
        airtest_mocks["swipe"].assert_called_once_with([100, 200], [300, 400])

    def test_wait_action(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        with patch("bot.engine.time.sleep") as m_sleep:
            runner._run_actions([{"wait": 0.01}])
            m_sleep.assert_called_once_with(0.01)

    def test_log_action_does_not_crash(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        runner._run_actions([{"log": "hello"}])

    def test_unknown_action_logs_warning(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        runner._run_actions([{"unknown_verb": 42}])

    def test_empty_actions(self, state_file, airtest_mocks):
        runner = make_runner(state_file, airtest_mocks)
        runner._run_actions([])
        runner._run_actions(None)


class TestTransitions:
    def test_transition_fires_when_visible(self, state_file, airtest_mocks):
        airtest_mocks["exists"].return_value = True
        runner = make_runner(state_file, airtest_mocks)
        runner.current_state = "menu"

        with patch("bot.engine.time.sleep"):
            runner.step()

        assert runner.current_state == "battle"

    def test_no_transition_when_not_visible(self, state_file, airtest_mocks):
        airtest_mocks["exists"].return_value = False
        runner = make_runner(state_file, airtest_mocks)
        runner.current_state = "menu"

        with patch("bot.engine.time.sleep"):
            runner.step()

        airtest_mocks["snapshot"].assert_called_once()

    def test_full_cycle_menu_to_battle_to_victory(self, state_file, airtest_mocks):
        visible_set = {"battle.png"}

        def fake_exists(tpl, **kw):
            return any(name in str(tpl) for name in visible_set)

        airtest_mocks["exists"].side_effect = fake_exists
        runner = make_runner(state_file, airtest_mocks)
        runner.current_state = "menu"

        with patch("bot.engine.time.sleep"):
            runner.step()
        assert runner.current_state == "battle"

        visible_set.clear()
        visible_set.add("victory.png")

        with patch("bot.engine.time.sleep"):
            runner.step()
        assert runner.current_state == "victory"


class TestRecovery:
    def test_unknown_state_saves_debug_screenshot(self, state_file, airtest_mocks):
        airtest_mocks["exists"].return_value = False
        runner = make_runner(state_file, airtest_mocks)
        runner.current_state = None

        runner.step()

        airtest_mocks["snapshot"].assert_called_once()
        args = airtest_mocks["snapshot"].call_args
        assert "unknown_" in args[1]["filename"]

    def test_redetects_state_when_current_is_unknown(self, state_file, airtest_mocks):
        airtest_mocks["exists"].side_effect = lambda tpl, **kw: "battle.png" in str(tpl)
        runner = make_runner(state_file, airtest_mocks)
        runner.current_state = None

        runner.step()

        assert runner.current_state == "battle"


class TestCallbacks:
    def test_on_state_change_called_on_transition(self, state_file, airtest_mocks):
        airtest_mocks["exists"].return_value = True
        callback = MagicMock()
        runner = make_runner(state_file, airtest_mocks, on_state_change=callback)
        runner.current_state = "menu"

        with patch("bot.engine.time.sleep"):
            runner.step()

        callback.assert_called_once_with("battle")

    def test_on_state_change_called_on_redetect(self, state_file, airtest_mocks):
        airtest_mocks["exists"].side_effect = lambda tpl, **kw: "menu.png" in str(tpl)
        callback = MagicMock()
        runner = make_runner(state_file, airtest_mocks, on_state_change=callback)
        runner.current_state = None

        runner.step()

        callback.assert_called_once_with("menu")

    def test_notifier_attribute_stored(self, state_file, airtest_mocks):
        notifier = MagicMock()
        runner = make_runner(state_file, airtest_mocks, notifier=notifier)
        assert runner.notifier is notifier
