#!/usr/bin/env python3
"""
Shiva AI — Module 1 : Auto-Repair 24/7
Surveille journalctl en temps réel, détecte les erreurs critiques,
interroge Ollama pour une solution, notifie via KDE.
"""
import subprocess
import json
import urllib.request
import urllib.error
import time
import os
import re
import logging

OLLAMA_URL  = "http://127.0.0.1:11434/api/generate"
MODEL       = "phi3:mini"
COOLDOWN    = 300   # secondes entre deux alertes pour la même erreur
LOG_FILE    = "/var/log/shiva-repair.log"
SEEN_ERRORS = {}
MAX_SEEN    = 500

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

CRITICAL_PATTERNS = [
    r"kernel panic",
    r"GPU hung",
    r"NVRM: GPU-\S+ Xid",
    r"Out of memory.*Killed process",
    r"EXT4-fs error",
    r"BTRFS.*error",
    r"drm.*error",
    r"amdgpu.*ERROR",
    r"i915.*ERROR",
    r"segfault at",
    r"general protection fault",
    r"BUG: unable to handle",
    r"WARNING: possible circular locking",
    r"ACPI Error",
]

def ask_ollama(error_text):
    prompt = (
        f"Tu es Shiva AI, assistant système pour Shiva OS (distro Linux gaming).\n"
        f"Erreur système détectée :\n{error_text}\n\n"
        f"Donne une explication en 2 lignes et une solution concrète en 1-2 commandes. "
        f"Réponse courte, en français, sans markdown."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        return f"Ollama indisponible : {e}"

def notify_kde(title, message, urgency="normal"):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva AI",
                        f"--urgency={urgency}", f"--icon=dialog-warning",
                        title, message], check=False)
    except Exception:
        pass

def is_new_error(line):
    key = line[:80]
    now = time.time()
    if key in SEEN_ERRORS and now - SEEN_ERRORS[key] < COOLDOWN:
        return False
    if len(SEEN_ERRORS) > MAX_SEEN:
        oldest = min(SEEN_ERRORS, key=SEEN_ERRORS.get)
        del SEEN_ERRORS[oldest]
    SEEN_ERRORS[key] = now
    return True

def monitor():
    logging.info("Shiva Repair démarré")
    proc = subprocess.Popen(
        ["journalctl", "-f", "-n", "0", "--no-pager", "-o", "short"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    for line in proc.stdout:
        line = line.strip()
        for pattern in CRITICAL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                if not is_new_error(line):
                    break
                logging.warning(f"ERREUR DÉTECTÉE : {line}")
                notify_kde("🔱 Shiva AI — Analyse en cours...",
                           f"Erreur détectée : {line[:100]}", "critical")
                solution = ask_ollama(line)
                logging.info(f"SOLUTION : {solution}")
                notify_kde("🔱 Shiva AI — Solution trouvée", solution, "critical")
                break

if __name__ == "__main__":
    monitor()
