#!/usr/bin/env python3
"""
Shiva AI — Module 2 : Optimisation Gaming Prédictive
Détecte les jeux lancés, applique gamemode + governor performance,
interroge Ollama pour des optimisations spécifiques au jeu.
"""
import subprocess
import json
import urllib.request
import time
import os
import re
import logging

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL      = "phi3:mini"
LOG_FILE   = "/var/log/shiva-optimizer.log"
STATE_FILE = "/tmp/shiva-gaming-active.json"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

GAME_PROCESSES = [
    "steam", "proton", "wine", "wineserver", "lutris",
    "heroic", "gamemode", "mangohud", "hl2_linux", "csgo",
    "dota2", "cyberpunk2077", "witcher3", "elden_ring",
    "eldenring", "sekiro", "darksouls", "pathofexile",
    "leagueoflegends", "valorant", "overwatch", "fortnite",
    "cod", "minecraft", "terraria", "stardew",
]

def notify(title, msg):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva AI",
                        "--icon=applications-games", title, msg], check=False)
    except Exception:
        pass

def get_running_games():
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        games = []
        for line in result.stdout.splitlines():
            for game in GAME_PROCESSES:
                if game.lower() in line.lower() and "grep" not in line:
                    name = line.split()[10] if len(line.split()) > 10 else game
                    games.append(os.path.basename(name))
        return list(set(games))
    except Exception:
        return []

def apply_performance_mode():
    # Governor CPU → performance
    try:
        for cpu in os.listdir("/sys/devices/system/cpu/"):
            gov = f"/sys/devices/system/cpu/{cpu}/cpufreq/scaling_governor"
            if os.path.exists(gov):
                with open(gov, "w") as f:
                    f.write("performance")
    except Exception:
        pass

    # GPU AMD → high performance
    try:
        dpm = "/sys/class/drm/card0/device/power_dpm_force_performance_level"
        if os.path.exists(dpm):
            with open(dpm, "w") as f:
                f.write("high")
    except Exception:
        pass

    # Désactiver CPU idle states profonds (latence réseau gaming)
    try:
        subprocess.run(["cpupower", "idle-set", "-D", "2"],
                       capture_output=True, check=False)
    except Exception:
        pass

def restore_balanced_mode():
    try:
        for cpu in os.listdir("/sys/devices/system/cpu/"):
            gov = f"/sys/devices/system/cpu/{cpu}/cpufreq/scaling_governor"
            if os.path.exists(gov):
                with open(gov, "w") as f:
                    f.write("schedutil")
    except Exception:
        pass
    try:
        dpm = "/sys/class/drm/card0/device/power_dpm_force_performance_level"
        if os.path.exists(dpm):
            with open(dpm, "w") as f:
                f.write("auto")
    except Exception:
        pass

def get_ollama_tips(game_name):
    prompt = (
        f"Tu es Shiva AI. Le jeu '{game_name}' vient d'être lancé sur Shiva OS (Linux, Proton/Wine).\n"
        f"Donne 2-3 optimisations Linux spécifiques à ce jeu (variables Proton, paramètres MangoHUD, "
        f"options launch Steam, etc.). Réponse ultra courte, en français, sans markdown."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return None

def load_state():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        if len(state.get("last_tips", {})) > 100:
            state["last_tips"] = {}
        return state
    except Exception:
        return {"gaming": False, "games": [], "last_tips": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def main():
    logging.info("Shiva Optimizer démarré")
    state = load_state()

    while True:
        games = get_running_games()
        is_gaming = len(games) > 0

        if is_gaming and not state["gaming"]:
            state["gaming"] = True
            state["games"]  = games
            apply_performance_mode()
            logging.info(f"Gaming détecté : {games}")
            notify("🔱 Shiva OS — Mode Gaming", f"Performance maximale activée pour : {', '.join(games[:2])}")

            for game in games[:2]:
                clean = re.sub(r'[^a-zA-Z0-9]', ' ', game).strip()
                if clean and clean not in state["last_tips"]:
                    tips = get_ollama_tips(clean)
                    if tips:
                        state["last_tips"][clean] = tips
                        notify(f"🔱 Shiva AI — Tips {clean}", tips)
                        logging.info(f"Tips {clean} : {tips}")

        elif not is_gaming and state["gaming"]:
            state["gaming"] = False
            state["games"]  = []
            restore_balanced_mode()
            logging.info("Session gaming terminée — mode balanced restauré")
            notify("🔱 Shiva OS", "Session gaming terminée. Mode économie d'énergie actif.")

        save_state(state)
        time.sleep(10)

if __name__ == "__main__":
    main()
