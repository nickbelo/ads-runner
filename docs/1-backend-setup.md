# Ads Runner Raspberry Pi 5 Deployment Guide

This guide sets up a fresh Raspberry Pi 5 to run Ads Runner as a kiosk display plus a LAN admin panel.

## What This Installs

- Player service: `http://localhost:3000`, shown full-screen on the TV by Chromium kiosk.
- Admin service: `http://raspberrypi-1.local:3001`, used to upload media, manage slides, and trigger deploys.
- Chromium kiosk autostart: `/home/pi/.config/autostart/ads-display.desktop`.
- Media storage: `/home/pi/ads-runner/media/slides`.
- Playlist file: `/home/pi/ads-runner/slides.json`.

## Assumptions

- Raspberry Pi OS Desktop is installed.
- The Linux user is `pi`.
- The repo lives at `/home/pi/ads-runner`.
- The repo remote is `git@github.com:nickbelo/ads-runner.git`.

The current Python code uses `/home/pi/ads-runner` as an absolute path, so keep the `pi` user and path unless you also update `app.py`, `upload_app.py`, `setup_auth.py`, and `ads-runner-sudoers`.

This project does not use SQLite in the current implementation. Slides are stored in `slides.json`, which was chosen because it is lighter and simpler for this single-device kiosk.

## 1. Prepare the Fresh Pi Before Cloning

On the new Raspberry Pi, download and run the prep script:

```bash
curl -fsSL https://raw.githubusercontent.com/nickbelo/ads-runner/main/scripts/prepare-rpi5.sh -o /tmp/prepare-rpi5.sh
chmod +x /tmp/prepare-rpi5.sh
/tmp/prepare-rpi5.sh
```

The script updates the OS, installs required packages, checks SSH, creates the Chromium desktop autostart entry, creates the GitHub deploy key, and prints the public key.

It also installs the blank cursor theme used by kiosk mode. If you want to skip that during prep, run:

```bash
INSTALL_BLANK_CURSOR=0 /tmp/prepare-rpi5.sh
```

Add the printed public key to GitHub:

```text
Repository > Settings > Deploy keys > Add deploy key
```

Use read-only access unless you plan to push from the Raspberry Pi.

If the script changed hostname or upgraded core OS packages, reboot:

```bash
sudo reboot
```

## 2. Enable Desktop Autologin

Chromium kiosk needs a desktop session after boot.

```bash
sudo raspi-config
```

Choose:

```text
System Options > Boot / Auto Login > Desktop Autologin
```

Reboot after changing this setting.

## 3. Clone the Repo

```bash
cd /home/pi
git clone git@github.com:nickbelo/ads-runner.git
cd /home/pi/ads-runner
```

## 4. Create the Python Environment

```bash
cd /home/pi/ads-runner
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p media/slides
```

## 5. Set the Admin Password

```bash
cd /home/pi/ads-runner
source venv/bin/activate
python setup_auth.py
```

This creates `/home/pi/ads-runner/.env` with:

- `SECRET_KEY`
- `ADMIN_PASSWORD_HASH`

Do not commit `.env`.

## 6. Install Passwordless Restart Permissions

The web admin deploy button restarts `ads-runner` and `ads-upload`. Install the limited sudoers file:

```bash
cd /home/pi/ads-runner
sudo cp ads-runner-sudoers /etc/sudoers.d/ads-runner
sudo chmod 440 /etc/sudoers.d/ads-runner
sudo visudo -cf /etc/sudoers.d/ads-runner
```

## 7. Install systemd Services

Create `/etc/systemd/system/ads-runner.service`:

```ini
[Unit]
Description=Ads Runner Media Slider
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ads-runner
ExecStart=/home/pi/ads-runner/venv/bin/gunicorn --workers 1 --bind 127.0.0.1:3000 --chdir /home/pi/ads-runner app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/ads-upload.service`:

```ini
[Unit]
Description=Ads Runner Upload Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ads-runner
ExecStart=/home/pi/ads-runner/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:3001 --chdir /home/pi/ads-runner upload_app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Do not create a system-level `ads-display.service` for Chromium on Raspberry Pi OS Desktop with labwc/Wayland. During testing, this was unreliable after reboot because GUI apps need the user's desktop session, not only systemd's boot target.

The prep script already creates `/home/pi/.config/autostart/ads-display.desktop`, which launches Chromium after Desktop Autologin starts. If you need to recreate it manually, use:

```bash
mkdir -p /home/pi/.config/autostart
cat > /home/pi/.config/autostart/ads-display.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Ads Runner Display
Exec=/bin/bash -c 'sleep 6 && chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --disable-translate --check-for-update-interval=31536000 --autoplay-policy=no-user-gesture-required http://localhost:3000'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

If your OS still uses the older binary name, replace `chromium` with `chromium-browser`.

Enable and start the backend services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ads-runner ads-upload
sudo systemctl start ads-runner ads-upload
```

## 8. Verify or Re-run Blank Cursor Setup

The prep script runs the blank cursor installer by default. If it was skipped, failed because the repo was not reachable, or you want to run it again after cloning:

```bash
cd /home/pi/ads-runner
chmod +x scripts/setup-blank-cursor.sh
./scripts/setup-blank-cursor.sh
sudo reboot
```

Rebooting is recommended so the desktop session picks up the cursor theme.

## 9. Verify

From the Pi:

```bash
curl http://localhost:3000/api/slides
curl -I http://localhost:3001/login
systemctl status ads-runner ads-upload
```

From a phone or laptop on the same Wi-Fi:

```text
http://raspberrypi-1.local:3001
```

Log in with the admin password you created in step 5.

If you are testing with Raspberry Pi Connect screen sharing instead of an HDMI display, remember that it can behave differently from a physical TV output. To isolate app issues from display-session issues, open a terminal inside the screen sharing session and run:

```bash
chromium --kiosk --autoplay-policy=no-user-gesture-required --noerrdialogs --disable-infobars http://localhost:3000
```

If that works, the Flask app is healthy and any remaining issue is likely desktop autostart or HDMI/session related.

## 10. Deploy Updates Later

Use the deploy button in the admin page, or run:

```bash
cd /home/pi/ads-runner
git fetch --all
git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt --quiet
sudo systemctl restart ads-runner
sudo systemctl restart ads-upload
```
