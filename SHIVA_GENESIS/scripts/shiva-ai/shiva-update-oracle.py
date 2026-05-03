#!/usr/bin/env python3
"""
Shiva AI — Update Oracle
Vérifie kernel/mesa/OS approuvés sur shivaos.com et notifie l'utilisateur.
Tourne via timer systemd toutes les 5 min.
"""
import subprocess, json, urllib.request, sys, re, os

SHIVAOS_BASE   = "https://shivaos.com"
KERNEL_COPR    = "bieszczaders/kernel-cachyos"
MESA_RELEASE   = "F44"

def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return r.read().decode().strip()
    except Exception:
        return None

def notify(title, msg, urgency="normal"):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva Update Oracle",
                        f"--urgency={urgency}", "--icon=system-software-update",
                        title, msg], check=False)
    except Exception:
        pass

def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""

# ── Versions installées ──────────────────────────────────────────────────────

def get_installed_kernel():
    """Retourne la version kernel installée ex: 7.0.1"""
    r = run(["uname", "-r"])
    m = re.match(r"^(\d+\.\d+\.\d+)", r)
    return m.group(1) if m else r

def get_installed_mesa():
    """Retourne la version mesa ex: 26.0.5"""
    v = run(["rpm", "-q", "mesa-libGL", "--queryformat", "%{VERSION}"])
    return v if v and "not installed" not in v else None

def get_shivaos_version():
    """Retourne la version ShivaOS installée ex: 44"""
    try:
        for line in open("/etc/os-release"):
            if line.startswith("VERSION_ID="):
                return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    return None

# ── Normalisation versions ───────────────────────────────────────────────────

def normalize_kernel(v):
    """7.0.1-cachyos1 → 7.0.1"""
    m = re.match(r"^(\d+\.\d+\.\d+)", v)
    return m.group(1) if m else v

def normalize_mesa(v):
    """26.0.5-3 → 26.0.5 | 26.0.5-3.fc44 → 26.0.5"""
    m = re.match(r"^(\d+\.\d+\.\d+)", v)
    return m.group(1) if m else v

def version_newer(approved, installed):
    """True si approved > installed (comparaison sémantique)."""
    try:
        a = tuple(int(x) for x in re.findall(r"\d+", approved)[:3])
        i = tuple(int(x) for x in re.findall(r"\d+", installed)[:3])
        return a > i
    except Exception:
        return approved != installed

# ── Analyse DNF (paquets en attente) ────────────────────────────────────────

GAMING_CRITICAL = [
    "kernel", "mesa", "libGL", "vulkan", "amdgpu", "radeon", "nvidia",
    "steam", "proton", "wine", "lutris", "pipewire", "wayland", "plasma",
    "gamemode", "mangohud", "dxvk",
]

def get_dnf_updates():
    out = run(["dnf", "check-update", "--quiet"])
    updates = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith(" ") and "." in parts[0]:
            updates.append({"name": parts[0], "version": parts[1]})
    return updates

def ask_groq(gaming_updates):
    cfg_file = "/etc/shiva-ai.conf"
    api_key = None
    try:
        for line in open(cfg_file):
            if line.startswith("groq_key="):
                api_key = line.split("=",1)[1].strip()
    except Exception:
        pass
    if not api_key:
        return None
    summary = "\n".join([f"- {u['name']} → {u['version']}" for u in gaming_updates[:8]])
    prompt = (
        f"Tu es Shiva Update Oracle. Ces paquets critiques gaming vont être mis à jour sur ShivaOS (Fedora 44) :\n"
        f"{summary}\n\n"
        f"Y a-t-il un risque de régression gaming ? Verdict en 2 lignes : SAFE / RISQUÉ / CRITIQUE + raison. Français."
    )
    payload = json.dumps({"model": "llama-3.3-70b-versatile",
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 200}).encode()
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    updates_available = []

    # 1. Vérifier kernel approuvé
    approved_kernel = fetch(f"{SHIVAOS_BASE}/kernel-approved.txt")
    if approved_kernel and "—" not in approved_kernel:
        installed_kernel = get_installed_kernel()
        ak = normalize_kernel(approved_kernel)
        if version_newer(ak, installed_kernel):
            updates_available.append({
                "type": "kernel",
                "approved": approved_kernel,
                "installed": installed_kernel,
                "msg": f"Kernel {approved_kernel} approuvé (installé: {installed_kernel})"
            })

    # 2. Vérifier mesa approuvé
    approved_mesa = fetch(f"{SHIVAOS_BASE}/mesa-approved.txt")
    if approved_mesa and "—" not in approved_mesa:
        installed_mesa = get_installed_mesa()
        if installed_mesa:
            am = normalize_mesa(approved_mesa)
            im = normalize_mesa(installed_mesa)
            if version_newer(am, im):
                updates_available.append({
                    "type": "mesa",
                    "approved": approved_mesa,
                    "installed": installed_mesa,
                    "msg": f"Mesa {approved_mesa} approuvé (installé: {installed_mesa})"
                })

    # 3. Vérifier version ShivaOS
    approved_os = fetch(f"{SHIVAOS_BASE}/version.txt")
    installed_os = get_shivaos_version()
    if approved_os and installed_os and approved_os != installed_os:
        try:
            if int(approved_os) > int(installed_os):
                updates_available.append({
                    "type": "os",
                    "approved": approved_os,
                    "installed": installed_os,
                    "msg": f"ShivaOS {approved_os} disponible (installé: {installed_os})"
                })
        except ValueError:
            pass

    # Notifier si mises à jour disponibles
    if updates_available:
        lines = [u["msg"] for u in updates_available]
        cmds = []
        for u in updates_available:
            if u["type"] == "kernel":
                cmds.append("shiva kernel-update")
            elif u["type"] == "mesa":
                cmds.append("shiva mesa-update")
            elif u["type"] == "os":
                cmds.append("shiva upgrade")
        body = "\n".join(lines) + "\n\nCommande : " + " | ".join(cmds)
        notify("🔱 Mises à jour ShivaOS disponibles", body, "normal")
        print("🔱 Mises à jour ShivaOS disponibles :")
        for u in updates_available:
            print(f"  • {u['msg']}")
    else:
        print("✅ ShivaOS à jour — aucune mise à jour approuvée en attente.")

    # 4. Analyser les mises à jour DNF en attente (gaming)
    dnf_updates = get_dnf_updates()
    gaming = [u for u in dnf_updates if any(k in u["name"].lower() for k in GAMING_CRITICAL)]
    if gaming:
        print(f"\n📦 {len(gaming)} paquets gaming en attente de dnf upgrade :")
        for u in gaming:
            print(f"  • {u['name']} → {u['version']}")
        verdict = ask_groq(gaming)
        if verdict:
            print(f"\n🔱 Verdict Shiva AI :\n{verdict}")
            urgency = "critical" if "CRITIQUE" in verdict.upper() or "RISQUÉ" in verdict.upper() else "normal"
            notify("🔱 Update Oracle — Paquets gaming", verdict, urgency)

    return 0

if __name__ == "__main__":
    sys.exit(main())
