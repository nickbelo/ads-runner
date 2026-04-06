#!/usr/bin/env bash
set -euo pipefail

# Fresh Raspberry Pi 5 bootstrap for Ads Runner.
# Run this before cloning the repository.

ADS_USER="${ADS_USER:-pi}"
ADS_HOME="/home/${ADS_USER}"
ADS_DIR="${ADS_HOME}/ads-runner"
HOSTNAME_VALUE="${ADS_HOSTNAME:-raspberrypi-1}"
INSTALL_BLANK_CURSOR="${INSTALL_BLANK_CURSOR:-1}"
REPO_RAW_BASE="${REPO_RAW_BASE:-https://raw.githubusercontent.com/nickbelo/ads-runner/main}"
AUTOSTART_DIR="${ADS_HOME}/.config/autostart"
AUTOSTART_FILE="${AUTOSTART_DIR}/ads-display.desktop"

if [[ "${EUID}" -eq 0 ]]; then
  echo "Please run this as the ${ADS_USER} user, not with sudo."
  echo "The script will ask for sudo only when it needs system changes."
  exit 1
fi

if [[ "$(id -un)" != "${ADS_USER}" ]]; then
  echo "WARNING: this project currently assumes /home/${ADS_USER}/ads-runner."
  echo "You are running as $(id -un). Set ADS_USER=$(id -un) only after updating the app paths and sudoers file."
  exit 1
fi

echo "==> Updating OS packages"
sudo apt update
sudo apt full-upgrade -y

echo "==> Installing required packages"
sudo apt install -y \
  git \
  curl \
  wget \
  unzip \
  ffmpeg \
  x11-apps \
  python3-pip \
  python3-venv \
  python3-pil

echo "==> Installing Chromium"
if ! sudo apt install -y chromium; then
  echo "chromium package was not available; trying chromium-browser instead."
  sudo apt install -y chromium-browser
fi

echo "==> Checking SSH service"
if systemctl list-unit-files ssh.service >/dev/null 2>&1; then
  if systemctl is-enabled ssh >/dev/null 2>&1 && systemctl is-active ssh >/dev/null 2>&1; then
    echo "SSH is already enabled and running."
  else
    echo "SSH is not fully enabled/running; enabling it now."
    sudo systemctl enable --now ssh
  fi
else
  echo "SSH service was not found. If needed, enable SSH from Raspberry Pi Imager or raspi-config."
fi

if [[ -n "${HOSTNAME_VALUE}" ]]; then
  CURRENT_HOSTNAME="$(hostname)"
  if [[ "${CURRENT_HOSTNAME}" != "${HOSTNAME_VALUE}" ]]; then
    echo "==> Setting hostname to ${HOSTNAME_VALUE}"
    sudo hostnamectl set-hostname "${HOSTNAME_VALUE}"
  else
    echo "==> Hostname already set to ${HOSTNAME_VALUE}"
  fi
fi

BROWSER_BIN="$(command -v chromium || command -v chromium-browser || true)"
if [[ -z "${BROWSER_BIN}" ]]; then
  BROWSER_BIN="/usr/bin/chromium"
fi

echo "==> Creating Chromium kiosk desktop autostart"
mkdir -p "${AUTOSTART_DIR}"
cat > "${AUTOSTART_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=Ads Runner Display
Exec=/bin/bash -c 'sleep 6 && ${BROWSER_BIN} --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-translate --check-for-update-interval=31536000 --autoplay-policy=no-user-gesture-required http://localhost:3000'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
chmod 644 "${AUTOSTART_FILE}"

if [[ "${INSTALL_BLANK_CURSOR}" == "1" ]]; then
  echo "==> Installing blank cursor theme for kiosk mode"
  CURSOR_SCRIPT="${ADS_DIR}/scripts/setup-blank-cursor.sh"
  if [[ -f "${CURSOR_SCRIPT}" ]]; then
    bash "${CURSOR_SCRIPT}"
  else
    TMP_CURSOR_SCRIPT="$(mktemp)"
    if curl -fsSL "${REPO_RAW_BASE}/scripts/setup-blank-cursor.sh" -o "${TMP_CURSOR_SCRIPT}"; then
      bash "${TMP_CURSOR_SCRIPT}"
    else
      echo "Could not download setup-blank-cursor.sh."
      echo "After cloning, run:"
      echo "  cd ${ADS_DIR}"
      echo "  ./scripts/setup-blank-cursor.sh"
    fi
    rm -f "${TMP_CURSOR_SCRIPT}"
  fi
else
  echo "==> Skipping blank cursor setup because INSTALL_BLANK_CURSOR=${INSTALL_BLANK_CURSOR}"
fi

echo "==> Checking target clone path"
if [[ -e "${ADS_DIR}" ]]; then
  echo "WARNING: ${ADS_DIR} already exists."
  echo "If it is not a git clone yet, move it before running git clone."
else
  echo "Clone target is available: ${ADS_DIR}"
fi

echo "==> Preparing SSH directory"
mkdir -p "${ADS_HOME}/.ssh"
chmod 700 "${ADS_HOME}/.ssh"

KEY_PATH="${ADS_HOME}/.ssh/github_deploy_key"
if [[ ! -f "${KEY_PATH}" ]]; then
  echo "==> Creating GitHub deploy key at ${KEY_PATH}"
  ssh-keygen -t ed25519 -C "rpi-ads-runner-${HOSTNAME_VALUE}" -f "${KEY_PATH}" -N ""
else
  echo "==> GitHub deploy key already exists at ${KEY_PATH}"
fi

SSH_CONFIG="${ADS_HOME}/.ssh/config"
if ! grep -q "IdentityFile ${KEY_PATH}" "${SSH_CONFIG}" 2>/dev/null; then
  echo "==> Adding GitHub deploy-key config"
  cat >> "${SSH_CONFIG}" <<EOF

Host github.com
  IdentityFile ${KEY_PATH}
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
EOF
  chmod 600 "${SSH_CONFIG}"
fi

echo
echo "==> Prep complete"
echo
echo "Add this public key to GitHub as a read-only Deploy Key:"
echo
cat "${KEY_PATH}.pub"
echo
echo "GitHub path:"
echo "  Repository > Settings > Deploy keys > Add deploy key"
echo
echo "Next steps:"
echo "  1. Reboot if the OS upgrade or hostname changed: sudo reboot"
echo "  2. Clone the repo: git clone git@github.com:nickbelo/ads-runner.git ${ADS_DIR}"
echo "  3. Continue with docs/1-backend-setup.md"
echo
echo "Blank cursor setup:"
echo "  The blank cursor installer was run during prep by default."
echo "  If it was skipped or failed, run this after cloning:"
echo "    cd ${ADS_DIR} && ./scripts/setup-blank-cursor.sh"
echo
echo "Kiosk autostart:"
echo "  Created ${AUTOSTART_FILE}"
echo "  Chromium will launch after Desktop Autologin starts the labwc session."
echo
echo "Reminder: enable Desktop Autologin with raspi-config before kiosk use:"
echo "  sudo raspi-config"
echo "  System Options > Boot / Auto Login > Desktop Autologin"
