#!/bin/bash
# Build ShivaOS 44 — base Fedora 44 KDE
# Branding + first-boot gaming + GRUB ShivaOS
set -e

ISO_IN="/home/freuja/Documents/moi/Fedora-KDE-Live-44.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_RC14.iso"
WORK="/home/freuja/Documents/moi/BUILD_shiva44"
ROOTFS="$WORK/rootfs"
EROFS_IMG="$WORK/new-squashfs.img"
ISO_STAGING="$WORK/iso-staging"
FED_MOUNT="/tmp/fed44-mount"
EROFS_MOUNT="/tmp/fed44-erofs"
BRANDING="/home/freuja/Documents/moi/branding"

echo "[S44] === Build ShivaOS 44 démarré $(date) ==="

# --- 1. Monter l'ISO et l'EROFS si pas déjà monté ---
mkdir -p "$WORK" "$FED_MOUNT" "$EROFS_MOUNT"
mountpoint -q "$FED_MOUNT" || mount -o loop "$ISO_IN" "$FED_MOUNT"
mountpoint -q "$EROFS_MOUNT" || mount -t erofs "$FED_MOUNT/LiveOS/squashfs.img" "$EROFS_MOUNT"
trap "umount '$EROFS_MOUNT' 2>/dev/null; umount '$FED_MOUNT' 2>/dev/null; echo '[S44] Cleanup done'" EXIT

# --- 2. Copier le rootfs EROFS vers répertoire modifiable ---
echo "[S44] Copie rootfs EROFS (~3 Go, quelques minutes)..."
rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"
cp -a "$EROFS_MOUNT/." "$ROOTFS/"
echo "[S44] Copie terminée."

# --- 3. BRANDING ---
echo "[S44] Application du branding ShivaOS 44..."

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

echo "shivaos44" > "$ROOTFS/etc/hostname"
sed -i 's/localhost\.localdomain/shivaos44/g; s/fedora/shivaos44/g' "$ROOTFS/etc/hosts" 2>/dev/null || true

# --- 4. WALLPAPER ---
echo "[S44] Wallpaper ShivaOS..."
mkdir -p "$ROOTFS/usr/share/wallpapers/ShivaOS/contents/images"
cp "$BRANDING/shivaos-wallpaper.png" \
   "$ROOTFS/usr/share/wallpapers/ShivaOS/contents/images/1920x1080.png"
cat > "$ROOTFS/usr/share/wallpapers/ShivaOS/metadata.json" << 'EOF'
{
    "KPlugin": {
        "Id": "ShivaOS",
        "Name": "ShivaOS",
        "Description": "ShivaOS Pure Gaming Ecosystem wallpaper"
    }
}
EOF

# Définir comme wallpaper par défaut via les look-and-feel
for LNF in \
    "$ROOTFS/usr/share/plasma/look-and-feel/org.fedoraproject.fedora.desktop/contents/defaults" \
    "$ROOTFS/usr/share/plasma/look-and-feel/org.kde.breeze.desktop/contents/defaults" \
    "$ROOTFS/usr/share/plasma/look-and-feel/org.kde.breezedark.desktop/contents/defaults"; do
    [ -f "$LNF" ] && sed -i \
        's|^Wallpaper=.*|Wallpaper=ShivaOS|g; s|^WallpaperPlugin=.*|WallpaperPlugin=org.kde.image|g' \
        "$LNF" 2>/dev/null || true
done

# Skel KDE pour forcer le wallpaper au premier login
mkdir -p "$ROOTFS/etc/skel/.config"
cat > "$ROOTFS/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc" << 'EOF'
[Containments][1][Wallpaper][org.kde.image][General]
Image=file:///usr/share/wallpapers/ShivaOS/contents/images/1920x1080.png
EOF

# --- 5. ICÔNES SHIVAOS (logo Kickoff) ---
for SIZE in 48 64 128 256; do
    mkdir -p "$ROOTFS/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps"
    cp "$BRANDING/shivaos-logo-256.png" \
       "$ROOTFS/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps/shivaos-logo.png" 2>/dev/null || true
done

# --- 6. SDDM — thème breeze-dark par défaut ---
mkdir -p "$ROOTFS/etc/sddm.conf.d"
cat > "$ROOTFS/etc/sddm.conf.d/shivaos.conf" << 'EOF'
[Theme]
Current=breeze
EOF

# --- 7. PLYMOUTH ShivaOS ---
if [ -d "$BRANDING/plymouth/shivaos" ]; then
    cp -r "$BRANDING/plymouth/shivaos" "$ROOTFS/usr/share/plymouth/themes/"
    # Activer le thème
    sed -i 's/^Theme=.*/Theme=shivaos/' "$ROOTFS/etc/plymouth/plymouthd.conf" 2>/dev/null || \
        printf '[Daemon]\nTheme=shivaos\n' > "$ROOTFS/etc/plymouth/plymouthd.conf"
fi

# --- 8. SHIVA FIRST-BOOT (DNF-based) ---
echo "[S44] Installation du service first-boot gaming..."
cat > "$ROOTFS/usr/local/bin/shiva-first-boot.sh" << 'FIRSTBOOT'
#!/bin/bash
# ShivaOS 44 — Premier démarrage réseau
STAMP="/var/lib/shivaos/.first-boot-done"
[ -f "$STAMP" ] && exit 0
mkdir -p /var/lib/shivaos

# Notif KDE
LIVEUSER=$(getent passwd 1000 | cut -d: -f1 2>/dev/null || echo liveuser)
sudo -u "$LIVEUSER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u "$LIVEUSER")/bus" \
    notify-send "ShivaOS 44" "Configuration gaming en cours... (~10 min)" --icon=shivaos-logo 2>/dev/null || true

# RPM Fusion (gaming drivers, Steam natif)
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

# Steam (Flatpak — plus fiable que RPM)
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
flatpak install -y --noninteractive flathub \
    com.valvesoftware.Steam \
    com.discordapp.Discord \
    com.obsproject.Studio \
    com.usebottles.bottles \
    com.heroicgameslauncher.hgl \
    com.sindresorhus.Caprine \
    2>/dev/null || true

# Ollama + modèle AI
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || true
systemctl enable ollama 2>/dev/null || true
systemctl start ollama 2>/dev/null || true
sleep 5
ollama pull phi3:mini 2>/dev/null || ollama pull llama3.2:1b 2>/dev/null || true

# Notif fin
sudo -u "$LIVEUSER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u "$LIVEUSER")/bus" \
    notify-send "ShivaOS 44" "Gaming prêt ! Steam, Lutris, Shiva AI actif." --icon=shivaos-logo 2>/dev/null || true

touch "$STAMP"
FIRSTBOOT
chmod +x "$ROOTFS/usr/local/bin/shiva-first-boot.sh"

cat > "$ROOTFS/usr/lib/systemd/system/shiva-first-boot.service" << 'EOF'
[Unit]
Description=ShivaOS First Boot Gaming Setup
After=network-online.target graphical.target
Wants=network-online.target
ConditionPathExists=!/var/lib/shivaos/.first-boot-done

[Service]
Type=oneshot
ExecStart=/usr/local/bin/shiva-first-boot.sh
TimeoutStartSec=1800
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Activer le service
mkdir -p "$ROOTFS/etc/systemd/system/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/shiva-first-boot.service \
    "$ROOTFS/etc/systemd/system/multi-user.target.wants/shiva-first-boot.service"

# --- 9. SHIVA AI MODULES ---
AI_SRC="/home/freuja/Documents/moi/SHIVA_GENESIS/scripts/shiva-ai"
if [ -d "$AI_SRC" ]; then
    mkdir -p "$ROOTFS/usr/share/shiva-ai"
    cp "$AI_SRC"/*.py "$ROOTFS/usr/share/shiva-ai/" 2>/dev/null || true
    ln -sf /usr/share/shiva-ai/shiva-assistant.py "$ROOTFS/usr/local/bin/shiva" 2>/dev/null || true
fi

# --- 10. CONF SHIVA AI ---
cat > "$ROOTFS/etc/shiva-ai.conf" << 'EOF'
backend=auto
groq_model=llama-3.3-70b-versatile
ollama_model=phi3:mini
EOF

# --- 10b. SHIVA AI — desktop entry ---
mkdir -p "$ROOTFS/usr/share/applications" "$ROOTFS/etc/skel/Desktop"
cat > "$ROOTFS/usr/share/applications/shiva-ai.desktop" << 'EOF'
[Desktop Entry]
Name=Shiva AI
Comment=Assistant gaming ShivaOS
Exec=konsole --noclose -e shiva
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;Game;
X-KDE-Plasma-DesktopFile-Trusted=true
EOF
cp "$ROOTFS/usr/share/applications/shiva-ai.desktop" "$ROOTFS/etc/skel/Desktop/shiva-ai.desktop"
chmod +x "$ROOTFS/etc/skel/Desktop/shiva-ai.desktop"

# --- 10c. REPO COPR ShivaOS ---
mkdir -p "$ROOTFS/etc/yum.repos.d"
cat > "$ROOTFS/etc/yum.repos.d/shivaos.repo" << 'EOF'
[shivaos]
name=ShivaOS 44 — Pure Gaming Ecosystem
baseurl=https://download.copr.fedorainfracloud.org/results/freuja/ShivaOs/fedora-$releasever-$basearch/
enabled=1
gpgcheck=1
gpgkey=https://download.copr.fedorainfracloud.org/results/freuja/ShivaOs/pubkey.gpg
repo_gpgcheck=0
EOF

# --- 11. SELinux — permissif pour la live session ---
sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' "$ROOTFS/etc/selinux/config" 2>/dev/null || true

# --- 12. Recompresser en EROFS ---
echo "[S44] Recompression EROFS (~5-10 min)..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -5
echo "[S44] EROFS créé: $(du -h "$EROFS_IMG" | cut -f1)"

# --- 13. Préparer l'ISO staging ---
echo "[S44] Préparation ISO staging..."
rm -rf "$ISO_STAGING"
mkdir -p "$ISO_STAGING/LiveOS" "$ISO_STAGING/boot/grub2"

# Copier tous les fichiers de l'ISO source sauf squashfs.img
cp -r "$FED_MOUNT/." "$ISO_STAGING/" 2>/dev/null || \
    xorriso -osirrox on -indev "$ISO_IN" -extract / "$ISO_STAGING/" 2>/dev/null
# Remplacer squashfs.img
cp "$EROFS_IMG" "$ISO_STAGING/LiveOS/squashfs.img"

# --- 14. GRUB — ShivaOS 44 branding ---
cat > "$ISO_STAGING/boot/grub2/grub.cfg" << 'GRUBEOF'
set default="1"

if [ "$grub_platform" == "efi" ]; then
    function load_video {
        insmod efi_gop
        insmod efi_uga
        insmod video_bochs
        insmod video_cirrus
        insmod all_video
    }
    set basicgfx="nomodeset"
else
    function load_video {
        insmod all_video
    }
    set basicgfx="nomodeset vga=791"
fi

load_video
set gfxpayload=keep
insmod gzio
insmod part_gpt
insmod ext2

terminal_input console
terminal_output console

set timeout=10
set timeout_style=menu

search --file --set=root /boot/0x6e8f9104

menuentry "ShivaOS 44 — Pure Gaming Ecosystem" --class fedora --class gnu-linux --class gnu --class os {
    linux ($root)/boot/x86_64/loader/linux quiet rhgb root=live:CDLABEL=Fedora-KDE-Live-44 rd.live.image selinux=0 enforcing=0
    initrd ($root)/boot/x86_64/loader/initrd
}
menuentry "ShivaOS 44 — Vérifier le média + démarrer" --class fedora --class gnu-linux --class gnu --class os {
    linux ($root)/boot/x86_64/loader/linux quiet rhgb root=live:CDLABEL=Fedora-KDE-Live-44 rd.live.image rd.live.check selinux=0 enforcing=0
    initrd ($root)/boot/x86_64/loader/initrd
}
submenu "Dépannage -->" {
    menuentry "ShivaOS 44 — Mode graphique basique" --class fedora --class gnu-linux --class gnu --class os {
        linux ($root)/boot/x86_64/loader/linux quiet rhgb root=live:CDLABEL=Fedora-KDE-Live-44 rd.live.image selinux=0 enforcing=0 ${basicgfx}
        initrd ($root)/boot/x86_64/loader/initrd
    }
}
GRUBEOF

# --- 15. Forge ISO finale ---
echo "[S44] Forge ISO ShivaOS 44..."
umount "$EROFS_MOUNT" 2>/dev/null || true
umount "$FED_MOUNT" 2>/dev/null || true
trap - EXIT

xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$ISO_STAGING/LiveOS/squashfs.img" /LiveOS/squashfs.img \
        -map "$ISO_STAGING/boot/grub2/grub.cfg" /boot/grub2/grub.cfg \
        -boot_image any replay 2>&1 | tail -10

echo "[S44] === Build terminé $(date) ==="
echo "[S44] ISO: $ISO_OUT"
echo "[S44] Taille: $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
