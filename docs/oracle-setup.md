# Oracle Cloud Free Tier setup

End-to-end walkthrough from "no Oracle account" to "bot running in the cloud."

## 1. Create Oracle Cloud account

1. Go to <https://signup.cloud.oracle.com>.
2. Pick a **home region** close to you. Riyadh users typically pick **me-jeddah-1** (Jeddah) or **me-dubai-1** (Dubai). **This is permanent** — you can't change your home region later.
3. Verify your credit card. Oracle won't charge it unless you explicitly upgrade to paid.

## 2. Generate an API key

Oracle Cloud Console → **Profile (top right) → My profile → API keys → Add API key**.

- Choose "Generate API key pair"
- Download both the public and private key (the private one goes to `~/.oci/oci_api_key.pem`)
- Copy the **configuration file preview** Oracle shows you — it has your `tenancy_ocid`, `user_ocid`, and `fingerprint`. Save those values.

```bash
mkdir -p ~/.oci
mv ~/Downloads/oci_api_key.pem ~/.oci/
chmod 600 ~/.oci/oci_api_key.pem
```

## 3. Generate an SSH key for the VM

Separate from the API key.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/oracle_rwtd -C "rwtd-bot"
```

## 4. Fill in Terraform vars

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with the OCIDs and fingerprint from step 2
```

## 5. Provision

```bash
terraform init
terraform apply
```

**Expect "Out of host capacity" errors.** Oracle's free ARM shapes are heavily oversubscribed. Terraform now tries **all availability domains** in your region automatically. Workarounds if all ADs fail:

- Re-run `terraform apply` every few hours. Hours-to-days is normal.
- A loop helps: `while ! terraform apply -auto-approve; do sleep 1800; done`
- Once an AD succeeds, pin it via `target_ad` in `terraform.tfvars` to avoid creating duplicate VMs.

Once it succeeds, note the `vm_public_ips` output.

## 6. Deploy

Cloud-init handles **system setup** on first boot, then **reboots the VM**:

1. Installs Docker (from Docker's official APT repo — Ubuntu's `docker.io` lacks `docker compose`)
2. **Downgrades the kernel to 5.15-oracle** — Oracle's default 6.8-oracle has a binder driver bug that wedges the host as soon as redroid's `servicemanager` starts. 5.15 works and ships `ashmem_linux` which 6.8 does not.
3. Configures `binder_linux` + `ashmem_linux` to auto-load on next boot
4. Clones the repo and copies `.env.example` to `.env`
5. Sets up a keep-alive cron (every 30 min) to prevent Oracle from reclaiming the VM
6. Reboots into the 5.15 kernel

The reboot is required — the kernel modules redroid needs only exist on 5.15. **Expect ~3-5 minutes total from `terraform apply` succeeding to SSH being available on the rebooted host.**

Cloud-init logs: `ssh ubuntu@<VM_IP> 'sudo cat /var/log/cloud-init-output.log'`

Verify after reboot:
```bash
ssh -i ~/.ssh/oracle_rwtd ubuntu@<VM_IP>
uname -r                # should be 5.15.0-1002-oracle
lsmod | grep -iE 'binder|ashmem'   # both should be loaded
```

Cloud-init does **NOT** auto-start the docker stack. SSH in and start it manually so you can watch logs:

```bash
cd ~/rwtd-cloud-bot
sudo docker compose -f docker/docker-compose.yml up   # foreground, watch logs
# Ctrl+C, then:
sudo docker compose -f docker/docker-compose.yml up -d # detach once stable
```

This was a deliberate choice: redroid first-boot is heavy and has wedged Always Free ARM VMs when run unattended via cloud-init. With manual start you can `Ctrl+C` if the VM gets sick.

## 7. First-time game install

The bot can't install the game for you (no Play Store login automation, deliberately — that's the line we don't cross). Do it once manually:

```bash
# Tunnel ADB to your local machine
ssh -i ~/.ssh/oracle_rwtd -L 5555:localhost:5555 ubuntu@<VM_IP>

# In another local terminal
adb connect localhost:5555
scrcpy -s localhost:5555
```

Use scrcpy to see the Android screen. Sign into Play Store with a **throwaway Google account**, install *Rogue with the Dead*, play through the tutorial. Once you reach the main menu, the bot should take over.

## 8. Keep the VM from being reclaimed

Oracle reclaims "idle" Always Free compute. Cloud-init already installs a cron job that runs every 30 minutes to keep the VM active. You can verify it's in place:

```bash
ssh ubuntu@<VM_IP> 'crontab -l'
```

## 9. Monitoring

- Healthcheck: `http://<VM_IP>:8080/`
- Discord alerts: set `DISCORD_WEBHOOK_URL` in `~/rwtd-cloud-bot/.env` on the VM, then `docker compose restart bot`.
- Logs: `ssh ... 'cd ~/rwtd-cloud-bot && docker compose -f docker/docker-compose.yml logs -f bot'`
- Debug screenshots: `~/rwtd-cloud-bot/screenshots/` — dumped whenever the bot enters an unknown state.

## Troubleshooting

**redroid won't start, "Operation not permitted" on binder.** The kernel modules didn't load. Re-run the modprobe commands from `scripts/deploy.sh` and check `dmesg`.

**Bot connects but Airtest can't see the screen.** Check `adb -s android:5555 shell getprop sys.boot_completed` returns `1`. redroid sometimes accepts ADB before the framework is up.

**Random app crashes.** Some apps need ARM translation. Use the `_ndk` variant of the redroid image (`redroid/redroid:12.0.0_64only-ndk`) — pixel-art games like *Rogue with the Dead* usually don't need this, but worth knowing.
