#!/bin/bash
# 🔱 SHIVA AI — Ollama + premier modèle (chroot safe)
echo "🔱 Installation de Shiva AI (Ollama)..."

# Télécharger et installer Ollama
curl -fsSL https://ollama.com/install.sh | OLLAMA_INSTALL_DIR=/usr/local sh 2>&1 || {
    mkdir -p /usr/local/bin
    curl -fsSL -o /usr/local/bin/ollama \
        "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64" || true
    chmod +x /usr/local/bin/ollama 2>/dev/null || true
}

# Créer l'utilisateur système ollama
useradd -r -s /bin/false -d /var/lib/ollama ollama 2>/dev/null || true
mkdir -p /var/lib/ollama
chown ollama:ollama /var/lib/ollama 2>/dev/null || true

# Service Ollama
cat > /etc/systemd/system/ollama.service << 'SVC'
[Unit]
Description=Shiva AI — Ollama LLM Server
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=127.0.0.1:11434"

[Install]
WantedBy=multi-user.target
SVC

# Script premier lancement : télécharge phi3:mini dès qu'il y a le réseau
mkdir -p /usr/share/shiva-store/
cat > /usr/share/shiva-store/shiva-ai-setup.sh << 'AISETUP'
#!/bin/bash
STAMP="/var/lib/ollama/.model-ready"
[ -f "$STAMP" ] && exit 0
notify-send "Shiva AI" "Téléchargement du modèle IA (phi3:mini ~2 Go)..." 2>/dev/null || true
systemctl start ollama 2>/dev/null || true
sleep 5
/usr/local/bin/ollama pull phi3:mini 2>/dev/null || \
    /usr/local/bin/ollama pull llama3.2:1b 2>/dev/null || true
touch "$STAMP"
notify-send "Shiva AI" "Shiva AI est prêt ! Dis : Hey Shiva... 🔱" 2>/dev/null || true
AISETUP
chmod +x /usr/share/shiva-store/shiva-ai-setup.sh

# Service one-shot pour télécharger le modèle au premier démarrage réseau
cat > /etc/systemd/system/shiva-ai-setup.service << 'SVC'
[Unit]
Description=Shiva AI — Download AI Model (first boot)
After=network-online.target ollama.service
Wants=network-online.target ollama.service
ConditionPathExists=!/var/lib/ollama/.model-ready

[Service]
Type=oneshot
ExecStart=/usr/share/shiva-store/shiva-ai-setup.sh
RemainAfterExit=yes
User=root

[Install]
WantedBy=multi-user.target
SVC

# Activer via symlinks (fonctionne dans chroot ET live)
MULTI_USER="/etc/systemd/system/multi-user.target.wants"
mkdir -p "$MULTI_USER"
ln -sf /etc/systemd/system/ollama.service      "$MULTI_USER/ollama.service"      2>/dev/null || true
ln -sf /etc/systemd/system/shiva-ai-setup.service "$MULTI_USER/shiva-ai-setup.service" 2>/dev/null || true

echo "✅ Ollama + Shiva AI Setup installés"
