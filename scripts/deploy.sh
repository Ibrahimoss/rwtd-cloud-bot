#!/usr/bin/env bash
# One-shot deployer for the Oracle Cloud VM after `terraform apply`.
#
# Reads VM_IP from terraform output, SSHes in, installs dependencies, and
# brings up the docker-compose stack.

set -euo pipefail

cd "$(dirname "$0")/.."

VM_IP="$(cd terraform && terraform output -raw vm_public_ip)"
SSH_USER="${SSH_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oracle_rwtd}"

echo "[deploy] Target: $SSH_USER@$VM_IP"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$SSH_USER@$VM_IP" bash <<'REMOTE'
set -euo pipefail

# --- Install Docker if missing ---
if ! command -v docker >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin git
  sudo usermod -aG docker "$USER"
fi

# --- Kernel modules required by redroid ---
sudo apt-get install -y linux-modules-extra-$(uname -r)
sudo modprobe binder_linux devices="binder,hwbinder,vndbinder" || true
sudo modprobe ashmem_linux || true

# Make them persistent across reboots
echo binder_linux | sudo tee /etc/modules-load.d/redroid.conf
echo ashmem_linux | sudo tee -a /etc/modules-load.d/redroid.conf
echo 'options binder_linux devices=binder,hwbinder,vndbinder' | sudo tee /etc/modprobe.d/redroid.conf

# --- Open firewall for healthcheck (NOT for ADB) ---
sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT || true

# --- Clone the repo ---
if [ ! -d ~/rwtd-cloud-bot ]; then
  git clone https://github.com/YOUR-USERNAME/rwtd-cloud-bot ~/rwtd-cloud-bot
fi
cd ~/rwtd-cloud-bot

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[deploy] WARNING: .env not configured. Edit ~/rwtd-cloud-bot/.env on the VM."
fi

# --- Bring up the stack ---
sg docker -c 'docker compose -f docker/docker-compose.yml up -d'
REMOTE

echo "[deploy] Done. SSH in to configure .env if first run:"
echo "  ssh -i $SSH_KEY $SSH_USER@$VM_IP"
echo "[deploy] To view the Android screen, tunnel ADB:"
echo "  ssh -i $SSH_KEY -L 5555:localhost:5555 $SSH_USER@$VM_IP"
echo "  scrcpy -s localhost:5555    # in another terminal"
