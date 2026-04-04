# Authentication approach for this setup:
# Since the admin panel runs on a local network on a lightweight RPi 5, we want something simple but solid — no heavy auth libraries, no database overhead. The right fit here is session-based login with a single admin password, stored as a hashed value in a .env config file. This means:

# A login page protects the admin panel
# Password is hashed with bcrypt — never stored in plain text
# Flask session cookie keeps you logged in
# A simple setup script lets you change the password anytime
# No user accounts or JWT complexity needed for a single-operator setup
# Check skill file for any relevant guidanceCheck skill file for any relevant guidanceNow let me build all the files.Created 3 files, edited a fileCreated 3 files, edited a fileNow update admin.html to add a logout button:Edited 2 filesEdited 2 filesNow update the requirements.txt to include bcrypt:Edited a file, created a file, read a fileEdited a file, created a file, read a fileFive files total. Here's exactly how to deploy them and get auth running.

# Deployment steps on the RPi
# 1 — Push files to the RPi and install bcrypt

# After committing to GitHub and pulling on the Pi, install the new dependency:

cd /home/pi/ads-runner
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# 2 — Run the setup script to set your password (one time only)

cd /home/pi/ads-runner
source venv/bin/activate
python3 setup_auth.py

# It will prompt you to enter and confirm a password, then write a hashed copy into /home/pi/ads-runner/.env. That file is never committed to GitHub.

# 3 — Add .env to .gitignore

echo ".env" >> /home/pi/ads-runner/.gitignore
git add .gitignore
git commit -m "ignore .env auth config"

# 4 — Restart the upload service

sudo systemctl restart ads-upload

# 5 — Test it

# Open http://raspberrypi-1.local:3001 from any device on the network — you should land on the login page. Enter your password and you'll be redirected to the admin panel. The "Sign out" button in the header clears the session.

# How it works in a nutshell:

# Every route in upload_app.py (pages and API calls) is wrapped with @login_required
# Passwords are hashed with bcrypt — the plain text is never stored anywhere
# Flask session cookie keeps you logged in across page loads
# If the session expires and the browser makes an API call, it gets a 401 response and is automatically redirected to /login
# To change the password later, just run python3 setup_auth.py again and restart the service