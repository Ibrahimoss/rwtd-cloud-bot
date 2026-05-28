# rwtd-cloud-bot

> A working template for deploying a self-hosted, 24/7 Android game automation bot on **free** cloud infrastructure.

Combines [redroid](https://github.com/remote-android/redroid-doc) (containerized Android), [Airtest](https://github.com/AirtestProject/Airtest) (Python automation layer), and Terraform (Oracle Cloud Free Tier provisioning) into one deployable stack. Includes a reference bot for *Rogue with the Dead: Idle RPG* as a working example.

**Fork it, swap in your own game, deploy in ~15 minutes.**

---

## What this is (and isn't)

**This is** a deployment recipe. The hard part of running a game bot 24/7 isn't the OpenCV — it's the plumbing: a stable Android environment, a free machine to host it, container networking, persistent storage, health monitoring, and a way to debug it remotely.

**This is not** a new automation framework. Airtest already exists and does the automation layer well. We use it. Credit where it's due.

## Why it exists

Plenty of game bots on GitHub. Almost none of them are deployable to a free cloud VM without a weekend of yak-shaving. This repo is the missing glue.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Oracle Cloud Free Tier — Ampere ARM, 4 vCPU, 24 GB │
│  ┌──────────────────┐    ┌──────────────────────┐   │
│  │   redroid        │    │   bot (Python)       │   │
│  │   Android 12     │◄──►│   Airtest + OpenCV   │   │
│  │   port 5555 ADB  │    │   state machine      │   │
│  └──────────────────┘    └──────────┬───────────┘   │
│                                     │               │
│                          ┌──────────▼───────────┐   │
│                          │ Discord notifier     │   │
│                          │ Health endpoint :8080│   │
│                          └──────────────────────┘   │
└──────────────────────────────────────────────────────┘
        ▲                                ▲
        │ scrcpy via SSH tunnel          │ HTTPS healthcheck
        │ (debug only)                   │ from your phone
```

## Quick start (local first)

You should always get this working on your dev machine before deploying. Docker Compose runs the same stack locally.

```bash
git clone https://github.com/YOUR-USERNAME/rwtd-cloud-bot
cd rwtd-cloud-bot
cp .env.example .env       # edit Discord webhook etc.
docker compose -f docker/docker-compose.yml up -d
```

Then connect a debug view from your host:

```bash
adb connect localhost:5555
scrcpy -s localhost:5555
```

You should see Android booting. Install the game manually once via Play Store (use a throwaway account), then the bot container will start grinding.

## Cloud deployment

See [`docs/oracle-setup.md`](docs/oracle-setup.md). TL;DR:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # add your Oracle creds
terraform init && terraform apply
# wait for VM, then:
./scripts/deploy.sh
```

## Swap in your own game

See [`docs/swap-in-your-own-game.md`](docs/swap-in-your-own-game.md). Short version:

1. Capture template PNGs of the buttons that matter in your game (`scripts/capture_template.py`).
2. Define your state machine in `bot/states/your_game.yaml`.
3. Point the bot at it in `.env`.

## Disclaimer

This project is for **educational and research purposes** — demonstrating mobile automation and cloud deployment techniques. The reference game (*Rogue with the Dead*) is single-player with no PvP, so automating it harms no other players. Most mobile games' Terms of Service prohibit automation; you are responsible for understanding the ToS of any game you choose to automate. **Use throwaway accounts.** Don't use this to circumvent in-app purchases, ads, or anti-cheat systems.

## Credits

- [Airtest](https://github.com/AirtestProject/Airtest) — the automation engine doing all the real work.
- [redroid](https://github.com/remote-android/redroid-doc) — the containerized Android that makes cloud deployment tractable.
- [abing7k/redroid-script](https://github.com/abing7k/redroid-script) — proved that redroid runs cleanly on Oracle Cloud Ampere ARM.

## License

MIT. See [LICENSE](LICENSE).
