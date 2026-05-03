#!/usr/bin/env python3
import hashlib
import json
import os
import datetime
import sys
import urllib.request
import urllib.parse

SALT = "SHIVA_GENESIS_PRIME"
PULSE_URL = "https://shivaos.com/pulse.php"
STATE_FILE = "/var/lib/shiva-pulse/state.json"

def get_machine_hash():
    try:
        with open("/etc/machine-id", "r") as f:
            machine_id = f.read().strip()
    except Exception:
        machine_id = "fallback"
    return hashlib.sha256((machine_id + SALT).encode()).hexdigest()

def already_pulsed_today():
    today = datetime.date.today().isoformat()
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        return state.get("last_pulse") == today
    except Exception:
        return False

def save_pulse_state():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"last_pulse": datetime.date.today().isoformat()}, f)

def send_pulse():
    machine_hash = get_machine_hash()
    url = f"{PULSE_URL}?machine_hash={urllib.parse.quote(machine_hash)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ShivaOS-Pulse/2.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "PULSE_RECEIVED":
                save_pulse_state()
                print("Pulse envoyé.")
            else:
                print(f"Réponse inattendue: {data}")
    except Exception as e:
        print(f"Erreur Pulse: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if already_pulsed_today():
        print("Pulse déjà envoyé aujourd'hui.")
        sys.exit(0)
    send_pulse()
