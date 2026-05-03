#!/usr/bin/env python3
"""
Shiva AI — Module 6 : Thermal Guard
Surveille CPU/GPU températures en temps réel.
Alerte avant throttling, Ollama explique la cause probable.
"""
import os
import glob
import time
import json
import urllib.request
import subprocess
import logging

OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
MODEL        = "phi3:mini"
LOG_FILE     = "/var/log/shiva-thermal.log"
INTERVAL     = 5       # secondes entre chaque lecture
CPU_WARN     = 85      # °C
CPU_CRIT     = 95      # °C
GPU_WARN     = 80      # °C
GPU_CRIT     = 90      # °C
COOLDOWN     = 120     # secondes entre deux alertes similaires

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

last_alert = {"cpu": 0, "gpu": 0}

def notify(title, msg, urgency="normal"):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva Thermal Guard",
                        f"--urgency={urgency}", "--icon=temperature",
                        title, msg], check=False)
    except Exception:
        pass

def read_cpu_temp():
    """Lit la température CPU depuis hwmon/thermal_zone."""
    sources = glob.glob("/sys/class/thermal/thermal_zone*/temp")
    temps = []
    for s in sources:
        try:
            with open(s) as f:
                t = int(f.read().strip()) / 1000
                if 0 < t < 120:
                    temps.append(t)
        except Exception:
            pass
    # Fallback : sensors
    if not temps:
        try:
            out = subprocess.run(["sensors", "-j"], capture_output=True, text=True)
            data = json.loads(out.stdout)
            for chip in data.values():
                for feat in chip.values():
                    if isinstance(feat, dict):
                        for k, v in feat.items():
                            if "input" in k and isinstance(v, (int, float)) and 0 < v < 120:
                                temps.append(float(v))
        except Exception:
            pass
    return round(max(temps), 1) if temps else None

def read_gpu_temp():
    """Lit la température GPU (AMD hwmon ou nvidia-smi)."""
    # AMD
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*/temp1_input"):
        try:
            name_file = hwmon.replace("temp1_input", "name")
            with open(name_file) as f:
                name = f.read().strip()
            if "amdgpu" in name or "radeon" in name:
                with open(hwmon) as f:
                    return round(int(f.read().strip()) / 1000, 1)
        except Exception:
            pass
    # NVIDIA
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True
        )
        return float(out.stdout.strip())
    except Exception:
        pass
    return None

def ask_ollama(component, temp, level):
    prompt = (
        f"Tu es Shiva Thermal Guard. {component} à {temp}°C (niveau {level}) sur Shiva OS.\n"
        f"Explique en 1 phrase la cause probable et donne 1 action immédiate. "
        f"Français, ultra court."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return None

def check_and_alert(name, temp, warn, crit, key):
    now = time.time()
    if temp is None:
        return
    if temp >= crit:
        if now - last_alert[key] > COOLDOWN:
            last_alert[key] = now
            logging.critical(f"{name} CRITIQUE : {temp}°C")
            tip = ask_ollama(name, temp, "CRITIQUE")
            msg = f"{name} à {temp}°C — THROTTLING IMMINENT !"
            if tip:
                msg += f"\n{tip}"
            notify(f"🌡️ ALERTE CRITIQUE — {name}", msg, "critical")
    elif temp >= warn:
        if now - last_alert[key] > COOLDOWN * 2:
            last_alert[key] = now
            logging.warning(f"{name} CHAUD : {temp}°C")
            tip = ask_ollama(name, temp, "élevé")
            msg = f"{name} à {temp}°C — surveille la ventilation."
            if tip:
                msg += f"\n{tip}"
            notify(f"⚠️ {name} chaud", msg, "normal")

def main():
    logging.info("Shiva Thermal Guard démarré")
    while True:
        cpu = read_cpu_temp()
        gpu = read_gpu_temp()
        if cpu:
            check_and_alert("CPU", cpu, CPU_WARN, CPU_CRIT, "cpu")
        if gpu:
            check_and_alert("GPU", gpu, GPU_WARN, GPU_CRIT, "gpu")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
