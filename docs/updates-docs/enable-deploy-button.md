# Let me plan this properly before writing any code.
# How the remote deploy trigger works:
# When the "Deploy" button is clicked in the admin panel, it calls a new /api/deploy endpoint in upload_app.py. That endpoint runs git pull on the RPi's repo directory, reinstalls dependencies if requirements.txt changed, and restarts the services via systemctl. The response streams back the output line by line so you can see exactly what happened — like a mini terminal in the browser.

# A few things to get right:

# sudo without password for systemctl — gunicorn runs as pi user, and systemctl restart normally needs sudo. We'll add a specific sudoers rule so only those two restart commands are allowed passwordless, nothing else.
# Streaming output — we use Flask's stream_with_context to stream the deploy log live to the browser so you don't stare at a spinner wondering if it hung.
# Lock to prevent double-deploys — a simple flag prevents two deploys running simultaneously if someone clicks twice.
# Security — the endpoint is already protected by @login_required, and the sudoers rule is scoped to only the two service restart commands.
# Viewed 2 filesViewed 2 filesGood. Now I have the full picture of both files. Let me build all the changes cleanly.Edited 3 filesEdited 3 filesNow add the deploy card and its styles to admin.html:Edited 3 files, viewed 3 filesEdited 3 files, viewed 3 filesGood. Now I'll add the deploy JS function right before the closing </script> tag:Add triggerDeploy function and toast div before closing script tagAdd triggerDeploy function and toast div before closing script tagNow add the missing <div id="toast"></div> which got displaced during the earlier edit:Viewed a file, edited a fileViewed a file, edited a fileNow create the sudoers config file:Created a file, read a fileCreated a file, read a fileThree files. Here's the full deployment sequence on your RPi.

# Deployment steps
# Step 1 — Install the sudoers rule (one time only)
# This is the most critical step. Without it, systemctl restart will fail silently inside the deploy because gunicorn runs as pi and can't call sudo without a password.
# bash# Copy the file into sudoers.d

sudo cp /home/pi/ads-runner/ads-runner-sudoers /etc/sudoers.d/ads-runner

# Set correct permissions (must be 440 or sudo will ignore it)
sudo chmod 440 /etc/sudoers.d/ads-runner

# Verify it parses without errors — this is important, a syntax error locks you out

sudo visudo -c -f /etc/sudoers.d/ads-runner

# You should see: /etc/sudoers.d/ads-runner: parsed OK
# Step 2 — Push and pull the updated code

bashcd /home/pi/ads-runner
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ads-upload

# Step 3 — Test it
# Open http://raspberrypi-1.local:3001, log in, and scroll down to the new Remote deploy card at the bottom. Click Deploy — you'll see a live terminal log stream in the page showing each step as it runs. When it finishes, the page reloads itself automatically.

# What happens during a deploy
# The log output is color-coded so you can see exactly what's happening:
# ColorMeaningGrayInformational step outputGreen [OK]Step completed successfullyYellow [WARN]Non-fatal warning (pip often writes to stderr)Red [ERROR]Step failed — deploy continues but result shows error
# One important thing to expect: when the last step (sudo systemctl restart ads-upload) runs, it restarts the very Flask process serving the page. The browser will briefly lose the connection mid-stream. The JS handles this gracefully — if the connection drops, it treats it as a successful restart, shows "services restarting", and reloads the page after 3.5 seconds.