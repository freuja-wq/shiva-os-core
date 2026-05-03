#!/usr/bin/env python3
"""
Shiva AI — Module 9 : Session Report Hebdomadaire
Compile les stats gaming de la semaine (MangoHUD + systemd logs).
Ollama génère un rapport personnalisé avec recommandations.
"""
import os
import json
import glob
import time
import re
import urllib.request
import subprocess
import logging
from datetime import datetime, timedelta

OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
MODEL        = "phi3:mini"
MANGOHUD_DIR = os.path.expanduser("~/.local/share/MangoHud/")
REPORT_DIR   = os.path.expanduser("~/.local/share/shiva-reports/")
LOG_DIR      = os.path.expanduser("~/.local/share/shiva-logs/")
LOG_FILE     = os.path.join(LOG_DIR, "session-report.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def notify(title, msg):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva Report",
                        "--icon=office-chart-bar", "--expire-time=10000",
                        title, msg], check=False)
    except Exception:
        pass

def parse_log(filepath):
    fps_vals, gpu_temps = [], []
    try:
        with open(filepath) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                p = line.split(",")
                try:
                    fps_vals.append(float(p[0]))
                    if len(p) > 4:
                        gpu_temps.append(float(p[4]))
                except Exception:
                    pass
    except Exception:
        return None
    if not fps_vals:
        return None
    return {
        "fps_avg": round(sum(fps_vals)/len(fps_vals), 1),
        "fps_min": round(min(fps_vals), 1),
        "duration_min": round(len(fps_vals) / 60, 1),
        "gpu_temp_avg": round(sum(gpu_temps)/len(gpu_temps), 1) if gpu_temps else None,
    }

def collect_week_stats():
    cutoff = time.time() - 7 * 86400
    os.makedirs(MANGOHUD_DIR, exist_ok=True)
    logs = glob.glob(os.path.join(MANGOHUD_DIR, "*.csv"))
    games = {}

    for log in logs:
        if os.path.getmtime(log) < cutoff:
            continue
        name_raw = os.path.basename(log)
        m = re.match(r"^(.+?)_\d{4}-\d{2}-\d{2}", name_raw)
        game = m.group(1).replace("_", " ") if m else name_raw
        stats = parse_log(log)
        if not stats:
            continue
        if game not in games:
            games[game] = {"sessions": 0, "total_min": 0, "fps_avgs": [], "gpu_temps": []}
        games[game]["sessions"] += 1
        games[game]["total_min"] += stats["duration_min"]
        games[game]["fps_avgs"].append(stats["fps_avg"])
        if stats["gpu_temp_avg"]:
            games[game]["gpu_temps"].append(stats["gpu_temp_avg"])

    summary = []
    for game, data in games.items():
        summary.append({
            "game": game,
            "sessions": data["sessions"],
            "total_hours": round(data["total_min"] / 60, 1),
            "fps_avg": round(sum(data["fps_avgs"])/len(data["fps_avgs"]), 1) if data["fps_avgs"] else 0,
            "gpu_temp_avg": round(sum(data["gpu_temps"])/len(data["gpu_temps"]), 1) if data["gpu_temps"] else None,
        })
    return sorted(summary, key=lambda x: x["total_hours"], reverse=True)

def ask_ollama(stats_summary):
    if not stats_summary:
        return "Aucune session gaming détectée cette semaine."

    top = stats_summary[:5]
    lines = "\n".join([
        f"- {s['game']} : {s['total_hours']}h, FPS moy {s['fps_avg']}"
        + (f", GPU {s['gpu_temp_avg']}°C" if s['gpu_temp_avg'] else "")
        for s in top
    ])
    total_h = round(sum(s["total_hours"] for s in stats_summary), 1)

    prompt = (
        f"Tu es Shiva AI. Voici le rapport gaming hebdomadaire de l'utilisateur sur Shiva OS :\n"
        f"Total : {total_h}h de jeu cette semaine\n{lines}\n\n"
        f"Génère un rapport bref (4-5 lignes) avec :\n"
        f"1. Un commentaire motivant sur la semaine\n"
        f"2. Le jeu le plus joué et ses perfs\n"
        f"3. Une recommandation d'optimisation si FPS < 60 ou GPU chaud\n"
        f"4. Un conseil pour la semaine prochaine\n"
        f"Ton et style : coach gaming bienveillant. Français."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        return f"Rapport non généré : {e}"

def save_report(report_text, stats):
    os.makedirs(REPORT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(REPORT_DIR, f"rapport-{today}.txt")
    with open(path, "w") as f:
        f.write(f"🔱 RAPPORT SHIVA OS — Semaine du {today}\n")
        f.write("=" * 50 + "\n\n")
        f.write(report_text + "\n\n")
        f.write("--- Détail sessions ---\n")
        for s in stats:
            f.write(f"  {s['game']} : {s['sessions']} sessions, {s['total_hours']}h, FPS {s['fps_avg']}\n")
    return path

def should_run_today():
    """Ne s'exécute qu'une fois par semaine (le lundi)."""
    today = datetime.now().weekday()
    return today == 0  # Lundi

def main():
    if not should_run_today():
        logging.info("Pas lundi — rapport ignoré")
        return
    logging.info("Shiva Session Report lancé")
    stats   = collect_week_stats()
    report  = ask_ollama(stats)
    path    = save_report(report, stats)
    total_h = round(sum(s["total_hours"] for s in stats), 1)

    logging.info(f"Rapport généré : {path}")
    notify(f"🔱 Rapport Gaming — {total_h}h cette semaine", report[:300] + "...")
    print(f"\n🔱 RAPPORT SHIVA OS\n{'='*40}\n{report}\n")
    print(f"Rapport complet : {path}")

if __name__ == "__main__":
    main()
