#!/usr/bin/env python3
"""
Shiva AI — Module 3 : Assistant "Hey Shiva"
Backend : proxy shivaos.com → Groq llama-3.3-70b
"""
import sys, os, json, time, urllib.request, subprocess, readline, atexit

GROQ_PROXY    = "https://shivaos.com/shiva-chat-proxy.php"
GROQ_TOKEN    = "shiva-os-2026"
FIFO_PATH     = "/tmp/shiva-assistant.fifo"
HISTORY_FILE  = os.path.expanduser("~/.shiva_history")
CONFIG_FILE   = "/etc/shiva-ai.conf"

SYSTEM_PROMPT = """Tu es Shiva AI, l'assistant intégré de Shiva OS — une distro Linux dédiée au gaming pur.
Tu connais parfaitement : Linux, Steam, Proton, Wine, Lutris, Heroic, MangoHUD, GameMode, drivers GPU (NVIDIA/AMD/Intel), optimisation système gaming.
Tu réponds en français, de façon concise et directe. Tu peux donner des commandes shell quand c'est utile.
Tu t'appelles Shiva ou Shiva AI. Ton symbole est le trident 🔱."""

HISTORY = []

# ── CONFIG ──────────────────────────────────────────────────────────────────

def read_config():
    cfg = {"backend": "auto"}
    if os.path.exists(CONFIG_FILE):
        try:
            for line in open(CONFIG_FILE):
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
        except Exception:
            pass
    return cfg


def write_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(f"backend=groq\ngroq_model=llama-3.3-70b-versatile\n")
        print(f"✅ Config sauvegardée dans {CONFIG_FILE}")
    except PermissionError:
        print(f"⚠ Relance avec sudo pour modifier {CONFIG_FILE}")

# ── BACKENDS ────────────────────────────────────────────────────────────────

def notify(msg):
    try:
        subprocess.run(["notify-send", "--app-name=Shiva AI",
                        "--icon=applications-games", "Shiva AI", msg], check=False)
    except Exception:
        pass

def stream_groq(prompt):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in HISTORY[-8:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({"messages": messages}).encode()
    req = urllib.request.Request(GROQ_PROXY, data=payload, headers={
        "Content-Type": "application/json",
        "X-Shiva-Token": GROQ_TOKEN
    })
    print("\n🔱 Shiva : ", end="", flush=True)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    response = data.get("reply", "")
    print(response)
    return response.strip()

def ask(prompt):
    try:
        return stream_groq(prompt)
    except Exception as e:
        msg = f"⚠ Shiva AI hors ligne (vérifie ta connexion internet) : {e}"
        print(f"\n🔱 Shiva : {msg}")
        return msg

# ── COMMANDES SPÉCIALES ──────────────────────────────────────────────────────

def cmd_fix():
    """shiva fix — diagnostic + corrections automatiques."""
    print("🔱 Shiva Fix — analyse du système...\n")
    checks = []
    # Vérifie services critiques
    for svc in ["ollama", "shiva-repair", "shiva-gaming-optimizer"]:
        r = subprocess.run(["systemctl", "is-active", svc],
                           capture_output=True, text=True)
        status = r.stdout.strip()
        checks.append(f"  {svc}: {status}")
    # Température CPU
    try:
        temps = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        checks.append(f"  CPU temp: {int(temps)//1000}°C")
    except Exception:
        pass
    # Espace disque
    r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    for line in r.stdout.splitlines()[1:2]:
        checks.append(f"  Disque /: {line.split()[4]} utilisé")

    diag = "\n".join(checks)
    print(diag)
    prompt = f"Voici le diagnostic système ShivaOS :\n{diag}\n\nDonne un résumé rapide et les actions à faire si nécessaire."
    ask(prompt)

def cmd_profile(game):
    """shiva profile <jeu> — crée un profil d'optimisation."""
    prompt = (f"Crée un profil d'optimisation Linux gaming pour '{game}' : "
              f"recommande les options Proton/Wine, MangoHUD config, GameMode, "
              f"variables d'environnement utiles. Format : liste courte, commandes concrètes.")
    ask(prompt)

def cmd_bench():
    """shiva bench — résumé IA d'un benchmark rapide."""
    print("🔱 Shiva Bench — collecte des infos système...\n")
    info = []
    for cmd in [["uname", "-r"], ["lscpu"], ["free", "-h"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            info.append(r.stdout.strip()[:300])
        except Exception:
            pass
    prompt = f"Voici les infos système :\n{'---'.join(info)}\n\nDonne une évaluation gaming rapide et 3 conseils d'optimisation."
    ask(prompt)

def cmd_config(args):
    """shiva config — affiche la config."""
    if not args:
        cfg = read_config()
        print(f"🔱 Shiva AI config ({CONFIG_FILE}):")
        for k, v in cfg.items():
            print(f"   {k} = {v}")
        return
    cfg = read_config()
    for arg in args:
        if "=" in arg:
            k, v = arg.split("=", 1)
            cfg[k.strip()] = v.strip()
            print(f"  {k.strip()} → {v.strip()}")
    write_config(cfg)

SHIVAOS_BASE = "https://shivaos.com"

def _fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return r.read().decode().strip()
    except Exception:
        return None

def _run_root(cmd):
    """Lance une commande avec pkexec (demande mot de passe graphiquement)."""
    import shutil
    if os.geteuid() == 0:
        return subprocess.run(cmd, check=False).returncode
    if shutil.which("pkexec"):
        return subprocess.run(["pkexec"] + cmd, check=False).returncode
    return subprocess.run(["sudo"] + cmd, check=False).returncode

def cmd_update():
    """shiva update — vérifie kernel/mesa/OS approuvés sur shivaos.com."""
    print("🔱 Shiva Update — vérification des mises à jour approuvées...\n")
    import re

    def fetch_ver(path):
        v = _fetch(f"{SHIVAOS_BASE}/{path}")
        return v if v and "—" not in v else None

    def ver_newer(a, b):
        try:
            return tuple(int(x) for x in re.findall(r"\d+", a)[:3]) > \
                   tuple(int(x) for x in re.findall(r"\d+", b)[:3])
        except Exception:
            return a != b

    has_update = False

    # Kernel
    approved_k = fetch_ver("kernel-approved.txt")
    if approved_k:
        installed_k = subprocess.run(["uname","-r"], capture_output=True, text=True).stdout.strip()
        ak = re.match(r"^(\d+\.\d+\.\d+)", approved_k)
        ik = re.match(r"^(\d+\.\d+\.\d+)", installed_k)
        if ak and ik and ver_newer(ak.group(1), ik.group(1)):
            print(f"  🔧 Kernel : {approved_k} disponible (installé : {installed_k})")
            print(f"     → lance : shiva kernel-update")
            has_update = True
        else:
            print(f"  ✅ Kernel à jour ({installed_k})")

    # Mesa
    approved_m = fetch_ver("mesa-approved.txt")
    if approved_m:
        inst_m = subprocess.run(["rpm","-q","mesa-libGL","--queryformat","%{VERSION}"],
                                 capture_output=True, text=True).stdout.strip()
        if inst_m and "not installed" not in inst_m:
            am = re.match(r"^(\d+\.\d+\.\d+)", approved_m)
            im = re.match(r"^(\d+\.\d+\.\d+)", inst_m)
            if am and im and ver_newer(am.group(1), im.group(1)):
                print(f"  🎨 Mesa : {approved_m} disponible (installé : {inst_m})")
                print(f"     → lance : shiva mesa-update")
                has_update = True
            else:
                print(f"  ✅ Mesa à jour ({inst_m})")

    # ShivaOS
    approved_os = fetch_ver("version.txt")
    inst_os = None
    try:
        for line in open("/etc/os-release"):
            if line.startswith("VERSION_ID="):
                inst_os = line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    if approved_os and inst_os:
        try:
            if int(approved_os) > int(inst_os):
                print(f"  🚀 ShivaOS {approved_os} disponible (installé : {inst_os})")
                print(f"     → lance : shiva upgrade")
                has_update = True
            else:
                print(f"  ✅ ShivaOS à jour (v{inst_os})")
        except ValueError:
            pass

    if not has_update:
        print("\n✅ Tout est à jour — aucune mise à jour approuvée en attente.")

def cmd_kernel_update():
    """shiva kernel-update — installe le kernel approuvé depuis COPR CachyOS."""
    approved = _fetch(f"{SHIVAOS_BASE}/kernel-approved.txt")
    if not approved or "—" in approved:
        print("⚠ Aucun kernel approuvé sur shivaos.com")
        return
    print(f"🔱 Installation kernel approuvé : {approved}")
    print("  Activation du repo CachyOS COPR...")
    _run_root(["dnf", "copr", "enable", "-y", "bieszczaders/kernel-cachyos"])
    print("  Installation en cours (dnf install kernel-cachyos)...")
    ret = _run_root(["dnf", "install", "-y", "kernel-cachyos"])
    if ret == 0:
        print(f"\n✅ Kernel {approved} installé. Redémarre pour l'activer.")
        notify("🔱 Kernel mis à jour", f"Kernel {approved} installé. Redémarre le PC.")
    else:
        print("\n⚠ Erreur lors de l'installation. Vérifie la connexion internet.")

def cmd_mesa_update():
    """shiva mesa-update — met à jour Mesa depuis les dépôts Fedora."""
    approved = _fetch(f"{SHIVAOS_BASE}/mesa-approved.txt")
    if not approved or "—" in approved:
        print("⚠ Aucune version Mesa approuvée sur shivaos.com")
        return
    print(f"🔱 Mise à jour Mesa approuvée : {approved}")
    print("  dnf upgrade mesa* en cours...")
    ret = _run_root(["dnf", "upgrade", "-y", "--refresh", "mesa*"])
    if ret == 0:
        print(f"\n✅ Mesa mis à jour. Redémarre la session KDE pour l'activer.")
        notify("🔱 Mesa mis à jour", f"Mesa {approved} installé. Redémarre la session.")
    else:
        print("\n⚠ Erreur lors de la mise à jour Mesa.")

def cmd_upgrade():
    """shiva upgrade — upgrade ShivaOS vers la version suivante (dnf system-upgrade)."""
    import re
    approved = _fetch(f"{SHIVAOS_BASE}/version.txt")
    inst_os = None
    try:
        for line in open("/etc/os-release"):
            if line.startswith("VERSION_ID="):
                inst_os = line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    if not approved or not inst_os:
        print("⚠ Impossible de vérifier la version ShivaOS.")
        return
    try:
        if int(approved) <= int(inst_os):
            print(f"✅ ShivaOS est déjà à jour (v{inst_os}). Aucune upgrade disponible.")
            return
    except ValueError:
        pass
    print(f"🔱 Upgrade ShivaOS {inst_os} → {approved}")
    print("  Cette opération va télécharger la nouvelle version Fedora.")
    print("  Le système redémarrera 2 fois. Continue ? [o/N] ", end="")
    try:
        rep = input().strip().lower()
    except Exception:
        rep = "n"
    if rep not in ("o", "oui", "y", "yes"):
        print("Annulé.")
        return
    print("\n  Étape 1 — Téléchargement des paquets...")
    _run_root(["dnf", "system-upgrade", "download", "-y", f"--releasever={approved}"])
    print("\n  Étape 2 — Redémarrage pour appliquer l'upgrade...")
    print("  Le PC va redémarrer dans 10 secondes. Sauvegarde ton travail !")
    import time; time.sleep(10)
    _run_root(["dnf", "system-upgrade", "reboot"])

def cmd_help():
    print("""🔱 Shiva AI — commandes disponibles

  shiva                       Mode interactif (chat)
  shiva "ta question"         Réponse directe
  shiva fix                   Diagnostic système + conseils IA
  shiva profile <jeu>         Profil optimisation pour un jeu
  shiva bench                 Évaluation gaming du système
  shiva update                Vérifie kernel/mesa/OS approuvés sur shivaos.com
  shiva kernel-update         Installe le kernel CachyOS approuvé
  shiva mesa-update           Met à jour Mesa vers la version approuvée
  shiva upgrade               Upgrade ShivaOS vers la version suivante
  shiva config                Affiche la configuration
  shiva-hardware-probe        Détecte GPU/CPU, configure drivers

Backend : Groq · Llama 3.3 70B via shivaos.com (proxy sécurisé)
""")

# ── MODES ───────────────────────────────────────────────────────────────────

def run_interactive():
    if os.path.exists(HISTORY_FILE):
        try:
            readline.read_history_file(HISTORY_FILE)
        except Exception:
            pass
    atexit.register(readline.write_history_file, HISTORY_FILE)
    readline.set_history_length(500)

    label = "Groq · Llama 3.3 70B"

    print(f"🔱 Shiva AI — {label}")
    print("   Tape 'exit' ou Ctrl+C pour quitter. 'help' pour les commandes.\n")

    while True:
        try:
            user_input = input("Toi : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n🔱 À bientôt, Légionnaire.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("🔱 Shiva AI : À la prochaine. Bonne chasse. 🎮")
            break
        if user_input.lower() == "help":
            cmd_help(); continue
        if user_input.lower() == "fix":
            cmd_fix(); continue
        if user_input.lower().startswith("profile "):
            cmd_profile(user_input[8:]); continue
        if user_input.lower() == "bench":
            cmd_bench(); continue
        if user_input.lower() == "update":
            cmd_update(); continue
        if user_input.lower() == "kernel-update":
            cmd_kernel_update(); continue
        if user_input.lower() == "mesa-update":
            cmd_mesa_update(); continue
        if user_input.lower() == "upgrade":
            cmd_upgrade(); continue

        HISTORY.append({"role": "user", "content": user_input})
        response = ask(user_input)
        HISTORY.append({"role": "assistant", "content": response})

def run_daemon():
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    os.mkfifo(FIFO_PATH)
    while True:
        try:
            with open(FIFO_PATH, "r") as f:
                question = f.read().strip()
            if question:
                HISTORY.append({"role": "user", "content": question})
                response = ask(question)
                HISTORY.append({"role": "assistant", "content": response})
                with open("/tmp/shiva-assistant-response.txt", "w") as f:
                    f.write(response)
                notify(response[:200])
        except Exception:
            time.sleep(1)

def ask_once(question):
    HISTORY.append({"role": "user", "content": question})
    response = ask(question)
    HISTORY.append({"role": "assistant", "content": response})
    return response

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        run_interactive()
    elif args[0] == "--daemon":
        run_daemon()
    elif args[0] == "fix":
        cmd_fix()
    elif args[0] == "bench":
        cmd_bench()
    elif args[0] == "help":
        cmd_help()
    elif args[0] == "update":
        cmd_update()
    elif args[0] == "kernel-update":
        cmd_kernel_update()
    elif args[0] == "mesa-update":
        cmd_mesa_update()
    elif args[0] == "upgrade":
        cmd_upgrade()
    elif args[0] == "config":
        cmd_config(args[1:])
    elif args[0] == "profile" and len(args) > 1:
        cmd_profile(" ".join(args[1:]))
    elif args[0] == "--ask" and len(args) > 1:
        ask_once(" ".join(args[1:]))
    else:
        ask_once(" ".join(args))
