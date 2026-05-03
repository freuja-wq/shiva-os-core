#!/bin/bash
# Patch v15 → v16
# Fixes: KWallet désactivé, SELinux applet supprimé, SDDM wallpaper ShivaOS,
#        logo "À propos" corrigé, liveinst-setup supprimé, shiva-first-boot user fix
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS_IMG="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v15.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v16.iso"
BRANDING="/home/freuja/Documents/moi/branding"

echo "[P44-v16] === Patch v16 démarré $(date) ==="

# --- 1. KWALLET — désactiver complètement ---
echo "[P44-v16] Désactivation KWallet..."
mkdir -p "$ROOTFS/etc/skel/.config"
cat > "$ROOTFS/etc/skel/.config/kwalletrc" << 'EOF'
[Wallet]
Enabled=false
First Use=false
EOF
# Aussi désactiver via xdg autostart
KWALLET_AUTOSTART="$ROOTFS/etc/xdg/autostart/pam_kwallet_init.desktop"
[ -f "$KWALLET_AUTOSTART" ] && echo "Hidden=true" >> "$KWALLET_AUTOSTART"

# --- 2. SELINUX APPLET — supprimer ---
echo "[P44-v16] Suppression sealertauto (SELinux désactivé)..."
rm -f "$ROOTFS/etc/xdg/autostart/sealertauto.desktop"

# --- 3. LIVEINST-SETUP — supprimer (pas besoin sur système installé) ---
echo "[P44-v16] Suppression liveinst-setup autostart..."
rm -f "$ROOTFS/etc/xdg/autostart/liveinst-setup.desktop"

# --- 4. SDDM — wallpaper ShivaOS ---
echo "[P44-v16] SDDM background ShivaOS..."
SDDM_WALL_DIR="$ROOTFS/usr/share/sddm/themes/breeze"
mkdir -p "$SDDM_WALL_DIR"
# Copier le wallpaper ShivaOS comme background SDDM
cp "$BRANDING/shivaos-wallpaper.png" "$SDDM_WALL_DIR/background.jpg" 2>/dev/null || \
cp "$BRANDING/shivaos-wallpaper.png" "$SDDM_WALL_DIR/background.png" 2>/dev/null || true
# Patcher le thème breeze SDDM pour utiliser notre wallpaper
THEME_CONF="$ROOTFS/usr/share/sddm/themes/breeze/theme.conf"
if [ -f "$THEME_CONF" ]; then
    sed -i 's|^background=.*|background=background.png|g' "$THEME_CONF"
    grep -q "^background=" "$THEME_CONF" || echo "background=background.png" >> "$THEME_CONF"
fi
cp "$BRANDING/shivaos-wallpaper.png" "$SDDM_WALL_DIR/background.png" 2>/dev/null || true

# --- 5. OS-RELEASE + LOGO KDE "À propos" ---
echo "[P44-v16] Fix logo À propos système..."
# KDE lit l'icône via LOGO= dans os-release → cherche dans hicolor
# Le nom doit correspondre exactement à un .png dans hicolor
cat > "$ROOTFS/etc/os-release" << 'EOF'
NAME="ShivaOS"
VERSION="44 (Pure Gaming Ecosystem)"
ID=shivaos
ID_LIKE=fedora
VERSION_ID=44
VERSION_CODENAME="genesis"
PRETTY_NAME="ShivaOS 44 — Pure Gaming Ecosystem"
ANSI_COLOR="1;38;2;255;100;0"
HOME_URL="https://shivaos.com"
BUG_REPORT_URL="https://shivaos.com"
LOGO=shivaos-logo
EOF
# S'assurer que l'icône existe bien dans hicolor/48x48 (taille lue par KDE Info Center)
for SIZE in 32 48 64 128 256; do
    DIR="$ROOTFS/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps"
    mkdir -p "$DIR"
    SRC="$BRANDING/shivaos-logo-256.png"
    [ -f "$BRANDING/shivaos-logo-${SIZE}.png" ] && SRC="$BRANDING/shivaos-logo-${SIZE}.png"
    cp "$SRC" "$DIR/shivaos-logo.png"
done
# Supprimer le fichier fedora-logo utilisé par KDE comme fallback
rm -f "$ROOTFS/usr/share/pixmaps/fedora-logo.png" 2>/dev/null || true
rm -f "$ROOTFS/usr/share/pixmaps/fedora-logo-sprite.png" 2>/dev/null || true

# --- 6. SHIVA-FIRST-BOOT — fix user dynamique (pas kubuntu codé en dur) ---
echo "[P44-v16] Fix shiva-first-boot user detection..."
cat > "$ROOTFS/usr/local/bin/shiva-first-boot.sh" << 'FIRSTBOOT'
#!/bin/bash
STAMP="/var/lib/shivaos/.first-boot-done"
[ -f "$STAMP" ] && exit 0
mkdir -p /var/lib/shivaos

# Détecter le vrai user (UID 1000)
REALUSER=$(getent passwd 1000 | cut -d: -f1 2>/dev/null || echo "")
[ -z "$REALUSER" ] && exit 1
USERHOME=$(getent passwd 1000 | cut -d: -f6)
USER_BUS="unix:path=/run/user/1000/bus"

_notify() {
    sudo -u "$REALUSER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="$USER_BUS" \
        notify-send "ShivaOS 44" "$1" --icon=shivaos-logo 2>/dev/null || true
}

_notify "Configuration gaming en cours... (~10 min)"

# RPM Fusion
dnf install -y \
    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
    "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm" \
    2>/dev/null || true

# Packages gaming
dnf install -y --setopt=install_weak_deps=False \
    mangohud gamemode \
    vulkan-tools mesa-vulkan-drivers \
    lutris \
    wget curl git ufw \
    python3 python3-requests \
    2>/dev/null || true

# Flatpak + Flathub
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
flatpak install -y --noninteractive flathub \
    com.valvesoftware.Steam \
    com.discordapp.Discord \
    com.obsproject.Studio \
    com.usebottles.bottles \
    com.heroicgameslauncher.hgl \
    com.sindresorhus.Caprine \
    2>/dev/null || true

# Ollama
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || true
systemctl enable --now ollama 2>/dev/null || true
sleep 5
sudo -u ollama ollama pull phi3:mini 2>/dev/null || \
    sudo -u ollama ollama pull llama3.2:1b 2>/dev/null || true

_notify "ShivaOS prêt ! Steam, Lutris, Shiva AI actif."
touch "$STAMP"
FIRSTBOOT
chmod +x "$ROOTFS/usr/local/bin/shiva-first-boot.sh"

# --- 7. Recompresser EROFS ---
echo "[P44-v16] Recompression EROFS (~5-10 min)..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -3
echo "[P44-v16] EROFS: $(du -h "$EROFS_IMG" | cut -f1)"

# --- 8. Forge ISO ---
echo "[P44-v16] Forge ISO v16..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS_IMG" /LiveOS/squashfs.img \
        -boot_image any replay 2>&1 | tail -5

echo "[P44-v16] === Terminé $(date) ==="
echo "[P44-v16] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
