#!/usr/bin/env python3
"""
Shiva AI — Module 5 : FPS Coach
Analyse les logs MangoHUD après chaque session gaming.
Ollama identifie les chutes de FPS et propose des optimisations.
"""
import os
import json
import re
import glob
import time
import urllib.request
import subprocess
import logging
from datetime import datetime

OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
MODEL        = "phi3:mini"
MANGOHUD_DIR = os.path.expanduser("~/.local/share/MangoHud/")
LOG_DIR      = os.path.expanduser("~/.local/share/shiva-logs/")
LOG_FILE     = os.path.join(LOG_DIR, "fps-coach.log")
ANALYZED     = set()
MAX_ANALYZED = 500

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def notify(title, msg):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva FPS Coach",
                        "--icon=applications-games", title, msg], check=False)
    except Exception:
        pass

def parse_mangohud_log(filepath):
    """Extrait les stats clés d'un log MangoHUD."""
    fps_values, gpu_temps, cpu_temps, frametimes = [], [], [], []
    try:
        with open(filepath) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                try:
                    fps_values.append(float(parts[0]))
                    if len(parts) > 4:
                        gpu_temps.append(float(parts[4]))
                    if len(parts) > 5:
                        cpu_temps.append(float(parts[5]))
                    if len(parts) > 1:
                        frametimes.append(float(parts[1]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        return None

    if not fps_values:
        return None

    drops = sum(1 for f in fps_values if f < (sum(fps_values)/len(fps_values)) * 0.6)
    return {
        "fps_avg":   round(sum(fps_values) / len(fps_values), 1),
        "fps_min":   round(min(fps_values), 1),
        "fps_max":   round(max(fps_values), 1),
        "fps_drops": drops,
        "gpu_temp_avg": round(sum(gpu_temps)/len(gpu_temps), 1) if gpu_temps else None,
        "cpu_temp_avg": round(sum(cpu_temps)/len(cpu_temps), 1) if cpu_temps else None,
        "session_len": len(fps_values),
    }

def ask_ollama(game_name, stats):
    prompt = (
        f"Tu es Shiva FPS Coach. Analyse cette session gaming '{game_name}' sur Linux :\n"
        f"FPS moyen: {stats['fps_avg']} | Min: {stats['fps_min']} | Max: {stats['fps_max']}\n"
        f"Chutes de FPS: {stats['fps_drops']} fois\n"
        f"Temp GPU: {stats.get('gpu_temp_avg','N/A')}°C | Temp CPU: {stats.get('cpu_temp_avg','N/A')}°C\n\n"
        f"Donne un diagnostic de 2 lignes et 2-3 optimisations concrètes pour améliorer ces perfs sur Shiva OS. "
        f"Français, concis, actionnable."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        return f"Analyse impossible : {e}"

def extract_game_name(filepath):
    name = os.path.basename(filepath)
    # MangoHud logs: "GameName_YYYY-MM-DD_HH:MM:SS.csv"
    match = re.match(r"^(.+?)_\d{4}-\d{2}-\d{2}", name)
    return match.group(1).replace("_", " ") if match else name

def watch():
    logging.info("Shiva FPS Coach démarré")
    os.makedirs(MANGOHUD_DIR, exist_ok=True)

    while True:
        logs = glob.glob(os.path.join(MANGOHUD_DIR, "*.csv"))
        if len(ANALYZED) > MAX_ANALYZED:
            ANALYZED.clear()
        for log in sorted(logs, key=os.path.getmtime, reverse=True)[:5]:
            if log in ANALYZED:
                continue
            age = time.time() - os.path.getmtime(log)
            if age > 120:  # Log de plus de 2 min = session terminée
                ANALYZED.add(log)
                stats = parse_mangohud_log(log)
                if not stats or stats["session_len"] < 60:
                    continue
                game = extract_game_name(log)
                logging.info(f"Analyse {game} : {stats}")
                notify(f"🔱 FPS Coach — {game}",
                       f"FPS moy: {stats['fps_avg']} | Min: {stats['fps_min']} — Analyse en cours...")
                tips = ask_ollama(game, stats)
                notify(f"🎮 FPS Coach — {game}", tips)
                logging.info(f"Conseils : {tips}")
        time.sleep(30)

if __name__ == "__main__":
    watch()
