# Contributing

Thanks for your interest. This project is intentionally small in scope —
its goal is to be a clean reference template, not a kitchen-sink framework.

## Welcome

- Bug fixes
- Documentation improvements
- Additional reference game implementations under `bot/states/`
- Compose/Terraform improvements for other cloud providers (Hetzner, Fly.io)
- Better debugging tools

## Probably out of scope

- Wrapping/replacing Airtest with a custom engine
- AI-decision-making at runtime (would change the project's character)
- Per-game balancing/optimization PRs for the reference game

## Code style

- `ruff check .` should pass.
- Keep dependencies minimal — every new package needs a justification.
- Docstrings on public functions, comments on non-obvious decisions.

## Disclaimer reminder

Any PR adding support for a new game must include a note in its docs
clarifying the ToS situation for that game. We don't ship support for
games where automation creates competitive harm (PvP, leaderboard-only
rewards, etc.).
