##### 1.1 — OS Prep

###### SSH into your Pi first:

ssh pi@raspberrypi-1.local

##### Update the system and install softwares

sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget unzip ffmpeg chromium xdotool python3-pip python3-venv

#### 1.2 — Install Node.js (needed even for Solution B for the upload tool's optional frontend build)

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v  # should show v20.x

#### 1.3 — Install Python dependencies

python3 -m venv /home/pi/ads-runner/venv
source /home/pi/ads-runner/venv/bin/activate
pip install flask flask-cors werkzeug gunicorn

#### 1.4 — GitHub deploy setup (git pull method — zero CI cost)
#### On the RPi, generate an SSH key and add it as a GitHub Deploy Key (read-only):

ssh-keygen -t ed25519 -C "rpi-ads-runner-keys" -f ~/.ssh/github_deploy_key -N ""
cat ~/.ssh/github_deploy_key.pub
# Copy this output → GitHub Repo → Settings → Deploy Keys → Add key

#### Configure SSH to use this key for GitHub:

cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/github_deploy_key
  StrictHostKeyChecking no
EOF

#### Clone the repo

cd /home/pi
git clone git@github.com:nickbelo/ads-runner.git

#### 1.3 — Install Python dependencies

python3 -m venv /home/pi/ads-runner/venv
source /home/pi/ads-runner/venv/bin/activate
pip install flask flask-cors werkzeug gunicorn

### Create a deploy script at /home/pi/deploy.sh:

cd /home/pi
nano deploy.sh

#!/bin/bash
cd /home/pi/ads-runner
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --quiet
sudo systemctl restart ads-runner
sudo systemctl restart ads-upload
echo "Deploy complete: $(date)"

chmod +x /home/pi/deploy.sh

# You can trigger this from your dev machine with:

ssh pi@raspberrypi-1.local '/home/pi/deploy.sh'

#### 1.5 — Display server setup (Wayland/X11)
#### Since you're on RPi OS with the 6.12 kernel, enable autologin and set the display properly:

sudo raspi-config
# → System Options → Boot / Auto Login → Desktop Autologin

#### 1.6 — systemd services
#### Create /etc/systemd/system/ads-runner.service:

sudo nano /etc/systemd/system/ads-runner.service

[Unit]
Description=Ads Runner Media Slider
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
WorkingDirectory=/home/pi/ads-runner
ExecStart=/home/pi/ads-runner/venv/bin/gunicorn -w 1 -b 127.0.0.1:3000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=graphical-session.target

#### Create /etc/systemd/system/ads-display.service (launches Chromium kiosk):

sudo nano /etc/systemd/system/ads-display.service

[Unit]
Description=Ads Runner Chromium Kiosk
After=ads-runner.service graphical-session.target
Wants=graphical-session.target

[Service]
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/bin/sleep 4
ExecStart=/usr/bin/chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-translate \
  --disable-features=TranslateUI \
  --check-for-update-interval=31536000 \
  --autoplay-policy=no-user-gesture-required \
  http://localhost:3000
Restart=always
RestartSec=10

[Install]
WantedBy=graphical-session.target

#### Create /etc/systemd/system/ads-upload.service:

sudo nano /etc/systemd/system/ads-upload.service

[Unit]
Description=Ads Runner Upload Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ads-runner
ExecStart=/home/pi/ads-runner/venv/bin/gunicorn -w 2 -b 0.0.0.0:3001 upload_app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

### Enable all services

sudo systemctl daemon-reload
sudo systemctl enable ads-runner ads-display ads-upload
sudo systemctl start ads-runner ads-uploads

#### PROJECT STRUCTURE

ads-runner/
├── app.py                  # Flask app — slide player backend
├── upload_app.py           # Flask app — upload & admin panel
├── requirements.txt
├── slides.json             # Playlist config (auto-generated)
├── media/
│   └── slides/            # uploaded files live here
└── templates/
    ├── player.html         # fullscreen slide player
    └── admin.html         # upload + playlist manager