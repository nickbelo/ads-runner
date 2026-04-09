#!/usr/bin/env bash
set -euo pipefail

# Post-clone installer for Ads Runner on Raspberry Pi 5.
# Run from /home/pi/ads-runner after prepare-rpi5.sh and git clone.

ADS_USER="${ADS_USER:-pi}"
ADS_HOME="/home/${ADS_USER}"
ADS_DIR="${ADS_DIR:-${ADS_HOME}/ads-runner}"

if [[ "${EUID}" -eq 0 ]]; then
  echo "Please run this as the ${ADS_USER} user, not with sudo."
  echo "The script will ask for sudo only when it needs system changes."
  exit 1
fi

if [[ "$(id -un)" != "${ADS_USER}" ]]; then
  echo "This installer currently assumes the ${ADS_USER} user and ${ADS_DIR}."
  echo "You are running as $(id -un)."
  exit 1
fi

if [[ ! -d "${ADS_DIR}" ]]; then
  echo "Repo directory not found: ${ADS_DIR}"
  echo "Clone the repo first, then run this script from the cloned repo."
  exit 1
fi

cd "${ADS_DIR}"

if [[ ! -f "requirements.txt" || ! -f "app.py" || ! -f "upload_app.py" ]]; then
  echo "This does not look like the ads-runner repo: ${ADS_DIR}"
  exit 1
fi

echo "==> Creating app data files and directories"
mkdir -p media/slides
if [[ ! -s slides.json ]]; then
  printf '[]\n' > slides.json
fi

echo "==> Creating Python virtual environment"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f ".env" ]]; then
  echo "==> Setting admin password"
  python setup_auth.py
else
  echo "==> .env already exists; keeping existing admin password"
fi

echo "==> Installing limited sudoers rule for deploy restarts"
sudo cp ads-runner-sudoers /etc/sudoers.d/ads-runner
sudo chmod 440 /etc/sudoers.d/ads-runner
sudo visudo -cf /etc/sudoers.d/ads-runner

echo "==> Installing ads-runner.service"
sudo tee /etc/systemd/system/ads-runner.service >/dev/null <<EOF
[Unit]
Description=Ads Runner Media Slider
After=network.target

[Service]
User=${ADS_USER}
WorkingDirectory=${ADS_DIR}
ExecStart=${ADS_DIR}/venv/bin/gunicorn --workers 1 --bind 127.0.0.1:3000 --chdir ${ADS_DIR} app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Installing ads-upload.service"
sudo tee /etc/systemd/system/ads-upload.service >/dev/null <<EOF
[Unit]
Description=Ads Runner Upload Service
After=network.target

[Service]
User=${ADS_USER}
WorkingDirectory=${ADS_DIR}
ExecStart=${ADS_DIR}/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:3001 --chdir ${ADS_DIR} --timeout 300 --graceful-timeout 30 upload_app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting backend services"
sudo systemctl daemon-reload
sudo systemctl enable ads-runner ads-upload
sudo systemctl restart ads-runner ads-upload

echo
echo "==> Install complete"
echo
echo "Check services:"
echo "  systemctl status ads-runner ads-upload"
echo
echo "Check APIs:"
echo "  curl http://localhost:3000/api/slides"
echo "  curl -I http://localhost:3001/login"
echo
echo "Admin panel:"
echo "  http://$(hostname).local:3001"
