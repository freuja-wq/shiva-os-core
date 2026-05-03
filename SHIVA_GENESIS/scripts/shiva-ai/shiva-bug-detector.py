#!/usr/bin/env python3
"""
Shiva AI — Module 4 : Détection de Bugs Proactive
Surveille dmesg, Xorg, Wayland, syslog en temps réel.
Alerte AVANT le crash avec explication Ollama.
"""
import subprocess
import json
import urllib.request
import time
import re
import logging
import os

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL      = "phi3:mini"
LOG_FILE   = "/var/log/shiva-bug-detector.log"
COOLDOWN   = 600
SEEN       = {}
MAX_SEEN   = 300

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

# Patterns avertisseurs (avant crash)
WARNING_PATTERNS = [
    (r"throttled due to",           "high",   "Throttling détecté"),
    (r"temperature.*above.*threshold","high",  "Température critique"),
    (r"drm.*hung.*ring",            "high",   "GPU potentiellement bloqué"),
    (r"NVRM.*Xid.*(\d+)",           "high",   "Erreur NVIDIA Xid"),
    (r"amdgpu.*ring.*timeout",      "high",   "Timeout AMD GPU"),
    (r"compositor.*crash",          "medium", "Crash compositor"),
    (r"memory.*low.*warning",       "medium", "RAM critique"),
    (r"disk.*I/O error",            "high",   "Erreur disque"),
    (r"EDAC.*error",                "medium", "Erreur mémoire RAM"),
    (r"undervoltage.*detected",     "medium", "Sous-tension détectée"),
    (r"kworker.*stuck",             "medium", "Kernel worker bloqué"),
    (r"blocked for more than.*seconds","medium","Processus bloqué"),
    (r"irq.*nobody cared",          "low",    "IRQ orpheline"),
    (r"possible firmware bug",      "medium", "Bug firmware potentiel"),
    (r"bad pmd",                    "high",   "Corruption mémoire virtuelle"),
]

def notify(title, msg, urgency="normal"):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva AI Bug Detector",
                        f"--urgency={urgency}", "--icon=dialog-error",
                        title, msg], check=False)
    except Exception:
        pass

def ask_ollama(error_type, raw_line):
    prompt = (
        f"Tu es Shiva AI. Erreur système '{error_type}' sur Shiva OS (Linux gaming) :\n"
        f"Log : {raw_line[:300]}\n\n"
        f"Explique en 1 phrase pourquoi c'est dangereux pour le gaming, "
        f"et donne 1 action corrective immédiate. Français, ultra court."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return None

def is_fresh(key):
    now = time.time()
    if key in SEEN and now - SEEN[key] < COOLDOWN:
        return False
    if len(SEEN) > MAX_SEEN:
        oldest = min(SEEN, key=SEEN.get)
        del SEEN[oldest]
    SEEN[key] = now
    return True

def monitor_source(source_cmd, source_name):
    def run():
        proc = subprocess.Popen(source_cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True)
        for line in proc.stdout:
            line = line.strip()
            for pattern, severity, label in WARNING_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    key = f"{label}:{line[:60]}"
                    if not is_fresh(key):
                        break
                    logging.warning(f"[{source_name}] {label}: {line}")
                    urgency = "critical" if severity == "high" else "normal"
                    notify(f"⚠️ Shiva AI — {label}", f"Analyse en cours...", urgency)
                    tip = ask_ollama(label, line)
                    if tip:
                        notify(f"⚠️ {label}", tip, urgency)
                        logging.info(f"Conseil : {tip}")
                    break
    import threading
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

def main():
    logging.info("Shiva Bug Detector démarré")
    threads = [
        monitor_source(["journalctl", "-f", "-n", "0", "--no-pager", "-k"], "kernel"),
        monitor_source(["journalctl", "-f", "-n", "0", "--no-pager", "-u", "display-manager"], "display"),
        monitor_source(["journalctl", "-f", "-n", "0", "--no-pager"], "system"),
    ]
    # Garder le processus en vie
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Shiva Bug Detector arrêté")

if __name__ == "__main__":
    main()
