# Ads Runner Operations Guide

Use this guide after the Raspberry Pi has been installed with `docs/1-backend-setup.md`.

## Project Layout

```text
ads-runner/
|-- app.py                  # Player backend on 127.0.0.1:3000
|-- upload_app.py           # Admin/upload backend on 0.0.0.0:3001
|-- setup_auth.py           # Creates/updates the admin password in .env
|-- ads-runner-sudoers      # Limited sudo rules for web deploy restarts
|-- requirements.txt        # Python dependencies
|-- slides.json             # Playlist config
|-- media/slides/           # Uploaded media files
|-- scripts/
|   |-- prepare-rpi5.sh     # Fresh Pi bootstrap script
|   |-- install-rpi5-services.sh
|   `-- setup-blank-cursor.sh
`-- templates/
    |-- player.html
    |-- login.html
    `-- admin.html
```

## Services

```text
ads-runner   Player Flask/Gunicorn service on port 3000
ads-upload   Admin Flask/Gunicorn service on port 3001
```

Chromium kiosk is launched by the desktop session through `/home/pi/.config/autostart/ads-display.desktop`. It is intentionally not a system service on Raspberry Pi OS Desktop with labwc/Wayland.

## Common Commands

Check services:

```bash
sudo systemctl status ads-runner ads-upload
```

Restart everything:

```bash
sudo systemctl restart ads-runner ads-upload
```

View logs:

```bash
journalctl -u ads-runner -f
journalctl -u ads-upload -f
```

Check kiosk autostart:

```bash
cat /home/pi/.config/autostart/ads-display.desktop
```

## Admin Access

Open this from any phone, tablet, or laptop on the same Wi-Fi:

```text
http://raspberrypi-1.local:3001
```

If mDNS is not resolving, use the Pi IP address:

```bash
hostname -I
```

Then open:

```text
http://<pi-ip-address>:3001
```

## Change Admin Password

```bash
cd /home/pi/ads-runner
source venv/bin/activate
python setup_auth.py
sudo systemctl restart ads-upload
```

## Deploy Latest Code

Preferred option: use the deploy button in the admin page.

Manual option:

```bash
cd /home/pi/ads-runner
git fetch --all
git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt --quiet
sudo systemctl restart ads-runner
sudo systemctl restart ads-upload
```

The admin deploy endpoint uses the same flow and restarts `ads-upload` in the background after the HTTP response is flushed.

## Backup and Restore

Back up playlist and media:

```bash
cd /home/pi/ads-runner
tar -czf /home/pi/ads-runner-backup-$(date +%Y%m%d).tar.gz slides.json media .env
```

Restore after copying a backup to the Pi:

```bash
cd /home/pi/ads-runner
tar -xzf /home/pi/ads-runner-backup-YYYYMMDD.tar.gz
sudo systemctl restart ads-runner ads-upload
```

## Troubleshooting

If the TV is blank:

```bash
sudo systemctl status ads-runner
journalctl -u ads-runner -n 100
curl http://localhost:3000/api/slides
cat /home/pi/.config/autostart/ads-display.desktop
pgrep -a chromium
```

If you are testing through Raspberry Pi Connect, launch Chromium manually from a terminal inside the screen sharing session:

```bash
chromium --kiosk --autoplay-policy=no-user-gesture-required --noerrdialogs --disable-infobars http://localhost:3000
```

If uploads fail:

```bash
sudo systemctl status ads-upload
journalctl -u ads-upload -n 100
ls -la /home/pi/ads-runner/media/slides
```

If the deploy button fails:

```bash
sudo visudo -cf /etc/sudoers.d/ads-runner
sudo -l
git -C /home/pi/ads-runner remote -v
git -C /home/pi/ads-runner fetch --all
```

If video duration detection does not work:

```bash
ffprobe -version
```

Install `ffmpeg` if missing:

```bash
sudo apt install -y ffmpeg
```

If the cursor appears in kiosk mode on Raspberry Pi OS with labwc/Wayland:

```bash
cd /home/pi/ads-runner
./scripts/setup-blank-cursor.sh
kill -HUP $(pgrep -u pi labwc) || sudo reboot
```
