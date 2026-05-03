#!/bin/bash
# 🔱 SHIVA AI — Installation complète des 10 modules
# À exécuter après le premier boot ou dans le chroot
AI_DIR="/usr/share/shiva-ai"
mkdir -p "$AI_DIR"

echo "🔱 Installation des 9 modules Shiva AI..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copier tous les modules
for module in shiva-repair shiva-gaming-optimizer shiva-assistant \
              shiva-bug-detector shiva-fps-coach shiva-thermal-guard \
              shiva-update-oracle shiva-compatibility-scout shiva-session-report \
              shiva-hardware-probe; do
    if [ -f "$SCRIPT_DIR/${module}.py" ]; then
        cp "$SCRIPT_DIR/${module}.py" "$AI_DIR/"
        chmod +x "$AI_DIR/${module}.py"
        echo "  ✅ $module"
    fi
done

# Lien symbolique pour l'assistant en ligne de commande
ln -sf "$AI_DIR/shiva-assistant.py" /usr/local/bin/shiva
chmod +x /usr/local/bin/shiva

# Lien pour Update Oracle (lancé avant apt upgrade)
ln -sf "$AI_DIR/shiva-update-oracle.py" /usr/local/bin/shiva-check-updates
chmod +x /usr/local/bin/shiva-check-updates

# Lien pour Hardware Probe (1er boot + reconfiguration manuelle)
ln -sf "$AI_DIR/shiva-hardware-probe.py" /usr/local/bin/shiva-hardware-probe
chmod +x /usr/local/bin/shiva-hardware-probe

# Config backend AI (auto = Groq si internet, Ollama sinon)
if [ ! -f /etc/shiva-ai.conf ]; then
    cat > /etc/shiva-ai.conf << 'CONF'
# Shiva AI — configuration backend
# backend = auto | groq | ollama
backend=auto
CONF
    echo "  ✅ /etc/shiva-ai.conf créé (backend=auto)"
fi

# ================================================================
# Services systemd
# ================================================================

# 1. Auto-Repair 24/7
cat > /etc/systemd/system/shiva-repair.service << 'SVC'
[Unit]
Description=Shiva AI — Auto-Repair 24/7
After=ollama.service network.target
Wants=ollama.service

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-repair.py
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
SVC

# 2. Gaming Optimizer
cat > /etc/systemd/system/shiva-gaming-optimizer.service << 'SVC'
[Unit]
Description=Shiva AI — Gaming Optimizer
After=ollama.service graphical.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-gaming-optimizer.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=graphical.target
SVC

# 3. Bug Detector
cat > /etc/systemd/system/shiva-bug-detector.service << 'SVC'
[Unit]
Description=Shiva AI — Bug Detector
After=ollama.service network.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-bug-detector.py
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
SVC

# 4. FPS Coach (surveille le dossier MangoHUD)
cat > /etc/systemd/system/shiva-fps-coach.service << 'SVC'
[Unit]
Description=Shiva AI — FPS Coach
After=ollama.service graphical.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-fps-coach.py
Restart=always
RestartSec=30
User=shiva

[Install]
WantedBy=graphical.target
SVC

# 5. Thermal Guard
cat > /etc/systemd/system/shiva-thermal-guard.service << 'SVC'
[Unit]
Description=Shiva AI — Thermal Guard
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-thermal-guard.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
SVC

# 6. Compatibility Scout
cat > /etc/systemd/system/shiva-compatibility-scout.service << 'SVC'
[Unit]
Description=Shiva AI — Compatibility Scout
After=ollama.service graphical.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-compatibility-scout.py
Restart=always
RestartSec=15
User=shiva

[Install]
WantedBy=graphical.target
SVC

# 7. Session Report (hebdomadaire le lundi)
cat > /etc/systemd/system/shiva-session-report.service << 'SVC'
[Unit]
Description=Shiva AI — Weekly Session Report
After=ollama.service network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-session-report.py
User=shiva
SVC

cat > /etc/systemd/system/shiva-session-report.timer << 'TIMER'
[Unit]
Description=Shiva AI — Weekly Report Timer

[Timer]
OnCalendar=Mon *-*-* 10:00:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
TIMER

# 8. Hardware Probe (one-shot au premier boot)
cat > /etc/systemd/system/shiva-hardware-probe.service << 'SVC'
[Unit]
Description=Shiva AI — Hardware Probe (first boot)
After=network.target ollama.service
ConditionPathExists=!/etc/shiva-hardware.json

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-hardware-probe.py
RemainAfterExit=yes
User=root

[Install]
WantedBy=multi-user.target
SVC

# 9. Update Oracle timer (vérifie mises à jour approuvées toutes les 5min)
cat > /etc/systemd/system/shiva-update-oracle.service << 'SVC'
[Unit]
Description=ShivaOS Update Oracle — vérification mises à jour approuvées

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-update-oracle.py
User=root
SVC

cat > /etc/systemd/system/shiva-update-oracle.timer << 'TIMER'
[Unit]
Description=ShivaOS Update Oracle — timer 5min

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
TIMER

# ================================================================
# Activation des services (symlinks — fonctionne chroot ET live)
# ================================================================
MULTI_USER="/etc/systemd/system/multi-user.target.wants"
GRAPHICAL="/etc/systemd/system/graphical.target.wants"
TIMERS="/etc/systemd/system/timers.target.wants"
mkdir -p "$MULTI_USER" "$GRAPHICAL" "$TIMERS"

for svc in shiva-repair shiva-bug-detector shiva-thermal-guard shiva-hardware-probe; do
    ln -sf "/etc/systemd/system/${svc}.service" "$MULTI_USER/${svc}.service" 2>/dev/null || true
done
for svc in shiva-gaming-optimizer shiva-fps-coach shiva-compatibility-scout; do
    ln -sf "/etc/systemd/system/${svc}.service" "$GRAPHICAL/${svc}.service" 2>/dev/null || true
done
ln -sf /etc/systemd/system/shiva-session-report.timer \
       "$TIMERS/shiva-session-report.timer" 2>/dev/null || true
ln -sf /etc/systemd/system/shiva-update-oracle.timer \
       "$TIMERS/shiva-update-oracle.timer" 2>/dev/null || true

echo ""
echo "🔱 SHIVA AI — 10 MODULES INSTALLÉS"
echo "  1. Auto-Repair 24/7        → systemd service"
echo "  2. Gaming Optimizer         → systemd service"
echo "  3. Assistant 'Hey Shiva'    → commande : shiva"
echo "  4. Bug Detector             → systemd service"
echo "  5. FPS Coach                → systemd service"
echo "  6. Thermal Guard            → systemd service"
echo "  7. Update Oracle            → hook apt automatique"
echo "  8. Compatibility Scout      → systemd service"
echo "  9. Session Report           → timer hebdomadaire lundi 10h"
echo " 10. Hardware Probe           → one-shot premier démarrage"
echo ""
echo "Lance l'assistant    : shiva"
echo "Vérifie les mises à jour : shiva-check-updates"
echo "Sonde le matériel    : shiva-hardware-probe [--force]"
