#!/usr/bin/env python3
"""
Shiva AI — Module 10 : Hardware Probe
Détecte GPU/CPU au premier démarrage, configure les drivers optimaux,
recommande les paramètres MangoHUD et GameMode adaptés au matériel.
"""
import subprocess
import json
import urllib.request
import os
import re
import sys
import logging

OLLAMA_URL  = "http://127.0.0.1:11434/api/generate"
MODEL       = "phi3:mini"
LOG_FILE    = "/var/log/shiva-hardware-probe.log"
STATE_FILE  = "/etc/shiva-hardware.json"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(message)s")

def notify(title, msg, urgency="normal"):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva Hardware Probe",
                        f"--urgency={urgency}", "--icon=computer",
                        title, msg], check=False)
    except Exception:
        pass

def detect_gpu():
    gpus = []
    try:
        out = subprocess.run(["lspci", "-nn"], capture_output=True, text=True)
        for line in out.stdout.splitlines():
            if re.search(r"VGA|3D|Display", line, re.IGNORECASE):
                gpus.append(line.strip())
    except Exception:
        pass
    return gpus

def detect_cpu():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Inconnu"

def detect_ram_gb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return round(kb / 1024 / 1024, 1)
    except Exception:
        pass
    return 0

def detect_gpu_vendor(gpus):
    for g in gpus:
        g_low = g.lower()
        if "nvidia" in g_low:
            return "nvidia"
        if "amd" in g_low or "radeon" in g_low:
            return "amd"
        if "intel" in g_low:
            return "intel"
    return "unknown"

def configure_amd():
    actions = []
    dpm = "/sys/class/drm/card0/device/power_dpm_force_performance_level"
    if os.path.exists(dpm):
        try:
            with open(dpm, "w") as f:
                f.write("auto")
            actions.append("AMD DPM : auto")
        except Exception:
            pass
    env_file = "/etc/environment"
    try:
        with open(env_file, "r") as f:
            content = f.read()
        additions = []
        if "RADV_PERFTEST" not in content:
            additions.append("RADV_PERFTEST=aco")
        if "AMD_VULKAN_ICD" not in content:
            additions.append("AMD_VULKAN_ICD=RADV")
        if additions:
            with open(env_file, "a") as f:
                f.write("\n# Shiva Hardware Probe — AMD optimizations\n")
                f.write("\n".join(additions) + "\n")
            actions.extend(additions)
    except Exception:
        pass
    return actions

def configure_nvidia():
    actions = []
    try:
        subprocess.run(["nvidia-smi", "--persistence-mode=1"],
                       capture_output=True, check=False)
        actions.append("NVIDIA persistence mode activé")
    except Exception:
        pass
    env_file = "/etc/environment"
    try:
        with open(env_file, "r") as f:
            content = f.read()
        if "__GL_THREADED_OPTIMIZATIONS" not in content:
            with open(env_file, "a") as f:
                f.write("\n# Shiva Hardware Probe — NVIDIA optimizations\n")
                f.write("__GL_THREADED_OPTIMIZATIONS=1\n")
                f.write("__GL_YIELD=NOTHING\n")
            actions.append("NVIDIA threaded optimizations activées")
    except Exception:
        pass
    return actions

def configure_cpu_governor():
    actions = []
    try:
        avail = open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors").read()
        governor = "schedutil" if "schedutil" in avail else "ondemand"
        for cpu_dir in os.listdir("/sys/devices/system/cpu/"):
            gov_path = f"/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_governor"
            if os.path.exists(gov_path):
                with open(gov_path, "w") as f:
                    f.write(governor)
        actions.append(f"CPU governor : {governor}")
    except Exception:
        pass
    return actions

def configure_zram():
    try:
        result = subprocess.run(["zramctl"], capture_output=True, text=True)
        if result.returncode == 0 and "/dev/zram" in result.stdout:
            return ["zram déjà actif"]
    except Exception:
        pass
    actions = []
    try:
        ram_gb = detect_ram_gb()
        zram_size = f"{min(int(ram_gb / 2), 8)}G"
        subprocess.run(["modprobe", "zram"], check=False, capture_output=True)
        subprocess.run(["zramctl", "--find", "--size", zram_size, "--algorithm", "zstd"],
                       check=False, capture_output=True)
        subprocess.run(["mkswap", "/dev/zram0"], check=False, capture_output=True)
        subprocess.run(["swapon", "--priority", "100", "/dev/zram0"],
                       check=False, capture_output=True)
        actions.append(f"zram swap activé ({zram_size}, zstd)")
    except Exception:
        pass
    return actions

def ask_ollama(cpu, gpus, ram_gb, vendor):
    prompt = (
        f"Tu es Shiva Hardware Probe. Configuration détectée sur Shiva OS (Linux gaming) :\n"
        f"CPU : {cpu}\nGPU : {', '.join(gpus) or 'inconnu'}\nRAM : {ram_gb} Go\n\n"
        f"Donne 3 recommandations d'optimisation gaming spécifiques à ce matériel "
        f"(Proton flags, variables d'env, réglages kernel, MangoHUD). "
        f"Format : bullet points courts, français, actionnable."
    )
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["response"].strip()
    except Exception:
        return None

def save_state(hw):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(hw, f, indent=2)
    except Exception:
        pass

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None

def main():
    logging.info("Shiva Hardware Probe démarré")

    state = load_state()
    force = "--force" in sys.argv

    if state and not force:
        print(f"🔱 Shiva Hardware Probe — matériel déjà configuré ({state.get('configured_at','')})")
        print(f"   GPU : {state.get('gpu_vendor','?')} | CPU : {state.get('cpu','?')[:50]}")
        print("   Lance avec --force pour reconfigurer.")
        return 0

    gpus   = detect_gpu()
    cpu    = detect_cpu()
    ram_gb = detect_ram_gb()
    vendor = detect_gpu_vendor(gpus)

    print(f"🔱 Shiva Hardware Probe")
    print(f"   CPU    : {cpu}")
    print(f"   GPU(s) : {', '.join(gpus) or 'non détecté'}")
    print(f"   RAM    : {ram_gb} Go")
    print(f"   Vendor : {vendor}")
    print()

    all_actions = []

    all_actions += configure_cpu_governor()

    if vendor == "amd":
        all_actions += configure_amd()
    elif vendor == "nvidia":
        all_actions += configure_nvidia()

    all_actions += configure_zram()

    print("⚙️ Optimisations appliquées :")
    for a in all_actions:
        print(f"   ✅ {a}")
        logging.info(a)

    tips = ask_ollama(cpu, gpus, ram_gb, vendor)
    if tips:
        print(f"\n🔱 Recommandations Shiva AI :\n{tips}")
        logging.info(f"Recommandations : {tips}")

    from datetime import datetime
    save_state({
        "cpu": cpu,
        "gpus": gpus,
        "gpu_vendor": vendor,
        "ram_gb": ram_gb,
        "actions": all_actions,
        "configured_at": datetime.now().isoformat(),
    })

    notify("🔱 Shiva Hardware Probe",
           f"Matériel configuré : {vendor.upper()} + {cpu[:40]}", "normal")

    return 0

if __name__ == "__main__":
    sys.exit(main())
