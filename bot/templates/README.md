# Templates

This directory holds PNG snippets of game UI elements that the bot matches
against live screenshots.

**Capture templates with:** `python scripts/capture_template.py`

Recommended templates for Rogue with the Dead:
- `main_menu_anchor.png` — a distinctive part of the main menu
- `in_run.png` — anchor visible while a run is active
- `death_screen.png` — anchor on the "you died" screen
- `victory_screen.png` — anchor on the "victory" screen
- `claim_button.png` — the gold/reward claim button
- `upgrade_button.png` — the upgrade button on the run screen

Crop tight. 60-120 px on the longer edge is usually enough. Avoid capturing
animated elements (counters, particles) — pick stable static UI.
