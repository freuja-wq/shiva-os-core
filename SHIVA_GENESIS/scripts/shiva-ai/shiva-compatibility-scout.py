#!/usr/bin/env python3
"""
Shiva AI — Module 8 : Compatibility Scout
Surveille les jeux récemment lancés, interroge ProtonDB + AreWeAntiCheatYet,
envoie une notif KDE avec le score de compatibilité Linux.
"""
import subprocess
import json
import urllib.request
import urllib.parse
import time
import os
import re
import logging

OLLAMA_URL    = "http://127.0.0.1:11434/api/generate"
MODEL         = "phi3:mini"
LOG_DIR       = os.path.expanduser("~/.local/share/shiva-logs/")
LOG_FILE      = os.path.join(LOG_DIR, "compatibility-scout.log")
CACHE_FILE    = os.path.expanduser("~/.cache/shiva-scout-cache.json")
ANTICHEAT_URL = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/master/games.json"
MAX_SEEN      = 200

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def notify(title, msg):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva Scout",
                        "--icon=applications-games", title, msg], check=False)
    except Exception:
        pass

def load_anticheat_db():
    cache_age = time.time() - os.path.getmtime(CACHE_FILE) if os.path.exists(CACHE_FILE) else 99999
    if cache_age < 86400:
        with open(CACHE_FILE) as f:
            return json.load(f)
    try:
        ctx = urllib.request.urlopen(ANTICHEAT_URL, timeout=15)
        data = json.loads(ctx.read())
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
        return data
    except Exception:
        return []

def search_protondb(appid):
    try:
        url = f"https://www.protondb.com/api/v1/reports/summaries/{appid}.json"
        ctx = urllib.request.urlopen(url, timeout=10)
        data = json.loads(ctx.read())
        return data.get("tier", "unknown"), data.get("bestReportedTier", "unknown")
    except Exception:
        return "unknown", "unknown"

def search_steam(game_name):
    try:
        url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(game_name)}&l=french&cc=FR"
        ctx = urllib.request.urlopen(url, timeout=10)
        data = json.loads(ctx.read())
        items = data.get("items", [])
        return items[0] if items else None
    except Exception:
        return None

def check_anticheat(game_name, ac_db):
    query = game_name.lower()
    for entry in ac_db:
        if query in (entry.get("name") or "").lower():
            return entry.get("status", "unknown"), entry.get("anticheats", [])
    return None, []

def ask_ollama(game_name, proton_tier, ac_status, anticheats):
    prompt = (
        f"Tu es Shiva Compatibility Scout. Résumé de compatibilité Linux pour '{game_name}' :\n"
        f"ProtonDB : {proton_tier}\n"
        f"Anti-cheat : {ac_status or 'inconnu'} ({', '.join(anticheats) or 'aucun détecté'})\n\n"
        f"Verdict en 2 lignes : peut-on jouer sur Shiva OS sans problème ? "
        f"Si anti-cheat bloquant, dis-le clairement. Français, court."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return f"ProtonDB: {proton_tier} | Anti-cheat: {ac_status or 'inconnu'}"

def get_recently_launched():
    """Détecte les nouveaux processus jeux via Steam runtime logs."""
    recently = set()
    try:
        out = subprocess.run(
            ["journalctl", "-u", "user@1000.service", "--since", "1 minute ago",
             "--no-pager", "-o", "short"],
            capture_output=True, text=True
        )
        for line in out.stdout.splitlines():
            m = re.search(r"steam_app_(\d+)", line)
            if m:
                recently.add(m.group(1))
    except Exception:
        pass
    return recently

def main():
    logging.info("Shiva Compatibility Scout démarré")
    ac_db      = load_anticheat_db()
    seen_apps  = set()
    ac_db_refresh = time.time()

    while True:
        if time.time() - ac_db_refresh > 86400:
            ac_db = load_anticheat_db()
            ac_db_refresh = time.time()
        if len(seen_apps) > MAX_SEEN:
            seen_apps.clear()
        app_ids = get_recently_launched()
        new_ids = app_ids - seen_apps

        for appid in new_ids:
            seen_apps.add(appid)
            logging.info(f"Nouveau jeu détecté : AppID {appid}")

            proton_tier, best_tier = search_protondb(appid)
            # Récupérer le nom via Steam
            try:
                url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=french"
                ctx = urllib.request.urlopen(url, timeout=10)
                data = json.loads(ctx.read())
                game_name = data.get(appid, {}).get("data", {}).get("name", f"App {appid}")
            except Exception:
                game_name = f"App {appid}"

            ac_status, anticheats = check_anticheat(game_name, ac_db)
            verdict = ask_ollama(game_name, proton_tier, ac_status, anticheats)

            emoji = "✅" if "platinum" in proton_tier or "gold" in proton_tier else \
                    "⚠️" if "silver" in proton_tier or "bronze" in proton_tier else "❌"
            notify(f"{emoji} Shiva Scout — {game_name}", verdict)
            logging.info(f"{game_name} : {proton_tier} | {ac_status}")

        time.sleep(15)

if __name__ == "__main__":
    main()
