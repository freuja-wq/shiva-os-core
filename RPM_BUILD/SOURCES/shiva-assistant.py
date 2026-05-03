#!/usr/bin/env python3
"""
Shiva AI — Assistant gaming ShivaOS
Backend : Groq Llama 3.3 70B (cloud, gratuit 14 400 req/jour)
"""
import sys, os, json, time, urllib.request, subprocess, readline, atexit

GROQ_API_KEY  = os.environ.get("GROQ_API_KEY", "")
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.3-70b-versatile"
FIFO_PATH     = "/tmp/shiva-assistant.fifo"
HISTORY_FILE  = os.path.expanduser("~/.shiva_history")

SYSTEM_PROMPT = """Tu es Shiva AI, l'assistant intégré de ShivaOS — une distro Linux dédiée au gaming pur.
Tu connais parfaitement : Linux, Steam, Proton, Wine, Lutris, Heroic, MangoHUD, GameMode, drivers GPU (NVIDIA/AMD/Intel), optimisation système gaming.
Tu réponds en français, de façon concise et directe. Tu peux donner des commandes shell quand c'est utile.
Tu t'appelles Shiva ou Shiva AI. Ton symbole est le trident 🔱."""

HISTORY = []

# ── GROQ ─────────────────────────────────────────────────────────────────────

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

    payload = json.dumps({
        "model": GROQ_MODEL, "messages": messages,
        "max_tokens": 1024, "temperature": 0.7, "stream": True
    }).encode()
    req = urllib.request.Request(GROQ_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    })
    response = ""
    print("\n🔱 Shiva : ", end="", flush=True)
    with urllib.request.urlopen(req, timeout=30) as r:
        for line in r:
            line = line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            token = json.loads(data).get("choices", [{}])[0].get("delta", {}).get("content", "")
            if token:
                print(token, end="", flush=True)
                response += token
    print()
    return response.strip()

def ask(prompt):
    try:
        return stream_groq(prompt)
    except Exception as e:
        msg = f"⚠ Shiva AI hors ligne (connexion requise) : {e}"
        print(f"\n🔱 {msg}")
        return msg

# ── COMMANDES SPÉCIALES ──────────────────────────────────────────────────────

def cmd_fix():
    print("🔱 Shiva Fix — analyse du système...\n")
    checks = []
    for svc in ["shiva-repair", "shiva-gaming-optimizer", "shiva-thermal-guard"]:
        r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
        checks.append(f"  {svc}: {r.stdout.strip()}")
    try:
        temps = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        checks.append(f"  CPU temp: {int(temps)//1000}°C")
    except Exception:
        pass
    r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    for line in r.stdout.splitlines()[1:2]:
        checks.append(f"  Disque /: {line.split()[4]} utilisé")
    diag = "\n".join(checks)
    print(diag)
    ask(f"Voici le diagnostic système ShivaOS :\n{diag}\n\nDonne un résumé rapide et les actions à faire si nécessaire.")

def cmd_profile(game):
    ask(f"Crée un profil d'optimisation Linux gaming pour '{game}' : "
        f"recommande les options Proton/Wine, MangoHUD config, GameMode, "
        f"variables d'environnement utiles. Format : liste courte, commandes concrètes.")

def cmd_bench():
    print("🔱 Shiva Bench — collecte des infos système...\n")
    info = []
    for cmd in [["uname", "-r"], ["lscpu"], ["free", "-h"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            info.append(r.stdout.strip()[:300])
        except Exception:
            pass
    ask(f"Voici les infos système :\n{'---'.join(info)}\n\nDonne une évaluation gaming rapide et 3 conseils d'optimisation.")

def cmd_help():
    print("""🔱 Shiva AI — commandes disponibles

  shiva                       Mode interactif (chat)
  shiva "ta question"         Réponse directe
  shiva fix                   Diagnostic système + conseils IA
  shiva profile <jeu>         Profil optimisation pour un jeu
  shiva bench                 Évaluation gaming du système

Backend : Groq · Llama 3.3 70B (cloud, gratuit, connexion requise)
""")

# ── MODES ────────────────────────────────────────────────────────────────────

def run_interactive():
    if os.path.exists(HISTORY_FILE):
        try:
            readline.read_history_file(HISTORY_FILE)
        except Exception:
            pass
    atexit.register(readline.write_history_file, HISTORY_FILE)
    readline.set_history_length(500)

    print("🔱 Shiva AI — Groq · Llama 3.3 70B")
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
    elif args[0] == "profile" and len(args) > 1:
        cmd_profile(" ".join(args[1:]))
    elif args[0] == "--ask" and len(args) > 1:
        ask_once(" ".join(args[1:]))
    else:
        ask_once(" ".join(args))
