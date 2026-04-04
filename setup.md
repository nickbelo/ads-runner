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



