# Swap in your own game

This repo's reference implementation is *Rogue with the Dead*, but the
plumbing is game-agnostic. To target a different idle/clicker mobile game:

## 1. Install the game in the running redroid

Use the same scrcpy tunnel approach in `oracle-setup.md` step 7 to install
and reach a stable starting state. Get to the screen you want the bot to
loop from.

## 2. Capture templates

On your dev machine, with the emulator running:

```bash
pip install opencv-python   # GUI-enabled, NOT -headless
python scripts/capture_template.py --host <emulator-ip> --port 5555
```

This pulls a screenshot, lets you drag-select a region, names it, saves it
to `bot/templates/`.

Capture one template per *anchor* — a small static UI element that's
visible only in that state. Avoid animated regions (gold counters,
particle effects).

## 3. Define your state machine

Copy `bot/states/rwtd.yaml` to `bot/states/yourgame.yaml` and rewrite:

```yaml
initial_state: main_menu

states:
  main_menu:
    detect: ../templates/yourgame_main_menu.png
    actions:
      - tap: [540, 1820]   # find these by hovering in capture tool
      - wait: 2
    transitions:
      - if_visible: ../templates/yourgame_playing.png
        to: playing
  playing:
    ...
```

## 4. Point the bot at it

In `.env`:

```
GAME_NAME=yourgame
STATE_MACHINE=bot/states/yourgame.yaml
```

Restart:

```bash
docker compose -f docker/docker-compose.yml restart bot
```

## Design tips

- **Keep loops short.** A state machine of 5-10 states is usually enough.
  More than that and you're probably modeling things at the wrong level.
- **Build in recovery.** When the bot enters an unknown state, it dumps a
  screenshot. Browse `screenshots/unknown_*.png` periodically and add
  states for whatever shows up.
- **Don't tap too fast.** Idle games are slow; 2-5 second waits between
  taps avoid race conditions and look more human.
- **Add a "panic" state.** A catch-all that taps the back button or center
  of screen if nothing matches for N polls. Recovers from popups.

## What this framework won't do for you

- Read text reliably (no built-in OCR — add Tesseract via Airtest if you
  need it).
- Handle CAPTCHAs (we explicitly don't try to bypass anti-bot measures).
- Make decisions that require real reasoning (e.g. "which artifact is
  better"). For that, you'd need to plug in a vision LLM at decision points
  — a future direction, not v1.
