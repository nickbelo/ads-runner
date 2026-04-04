#!/usr/bin/env python3
"""
Ads Runner — Auth Setup
Run this once to set or change the admin password.

Usage:
    python3 setup_auth.py
"""

import os
import secrets
import getpass

try:
    import bcrypt
except ImportError:
    print("Installing bcrypt...")
    os.system("pip install bcrypt --break-system-packages")
    import bcrypt

BASE_DIR = '/home/pi/ads-runner'
ENV_FILE = os.path.join(BASE_DIR, '.env')


def generate_secret_key():
    return secrets.token_hex(32)


def set_password():
    print("\n=== Ads Runner — Admin Password Setup ===\n")

    while True:
        password = getpass.getpass("Enter new admin password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters. Try again.\n")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Try again.\n")
            continue
        break

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Read existing .env if it exists so we preserve SECRET_KEY
    existing = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    existing[k.strip()] = v.strip()

    secret_key = existing.get('SECRET_KEY') or generate_secret_key()

    with open(ENV_FILE, 'w') as f:
        f.write("# Ads Runner — Auth Config\n")
        f.write("# Do not share or commit this file\n\n")
        f.write(f"SECRET_KEY={secret_key}\n")
        f.write(f"ADMIN_PASSWORD_HASH={hashed}\n")

    os.chmod(ENV_FILE, 0o600)  # owner read/write only

    print(f"\nPassword set successfully.")
    print(f"Config saved to: {ENV_FILE}")
    print(f"\nRestart the upload service to apply:")
    print(f"  sudo systemctl restart ads-upload\n")


if __name__ == '__main__':
    set_password()