#!/bin/bash
# Patch ShivaOS 44 — fixes restants (wallpaper, plasma-welcome, SDDM, Plymouth, pulse)
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS_IMG="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v12.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v13.iso"
BRANDING="/home/freuja/Documents/moi/branding"
AI_SRC="/home/freuja/Documents/moi/SHIVA_GENESIS/scripts/shiva-ai"

echo "[P44] === Patch ShivaOS 44 démarré $(date) ==="

# --- 1. PLASMA-WELCOME / KDE INITIAL SETUP — désactiver ---
echo "[P44] Désactivation plasma-welcome et KDE setup wizard..."
# Fedora KDE : plasma-welcome au premier login
for f in \
    "$ROOTFS/usr/share/autostart/org.kde.welcome.desktop" \
    "$ROOTFS/etc/xdg/autostart/org.kde.welcome.desktop" \
    "$ROOTFS/usr/share/autostart/plasma-welcome.desktop" \
    "$ROOTFS/etc/xdg/autostart/plasma-welcome.desktop" \
    "$ROOTFS/usr/share/autostart/org.fedoraproject.initial-setup.desktop" \
    "$ROOTFS/etc/xdg/autostart/org.fedoraproject.initial-setup.desktop"; do
    [ -f "$f" ] && { echo "Hidden=true" >> "$f"; sed -i 's/^Exec=.*/Exec=true/' "$f"; }
done
# Désactiver initial-setup service
ln -sf /dev/null "$ROOTFS/etc/systemd/system/initial-setup.service" 2>/dev/null || true
ln -sf /dev/null "$ROOTFS/etc/systemd/system/initial-setup-graphical.service" 2>/dev/null || true
# plasma-welcomerc
mkdir -p "$ROOTFS/etc/skel/.config"
cat > "$ROOTFS/etc/skel/.config/plasma-welcomerc" << 'EOF'
[General]
LastStartedVersion=99.0.0
ShowOnStartup=false
EOF

# --- 2. WALLPAPER — forcer ShivaOS dans tous les look-and-feel Fedora ---
echo "[P44] Fix wallpaper agressif..."
# Wallpaper v2 si disponible
WALL_SRC="$BRANDING/shivaos-wallpaper.png"
[ -f "$BRANDING/shivaos-wallpaper-v2.png" ] && WALL_SRC="$BRANDING/shivaos-wallpaper-v2.png"
mkdir -p "$ROOTFS/usr/share/wallpapers/ShivaOS/contents/images"
cp "$WALL_SRC" "$ROOTFS/usr/share/wallpapers/ShivaOS/contents/images/1920x1080.png"
cp "$WALL_SRC" "$ROOTFS/usr/share/wallpapers/ShivaOS/contents/images/3840x2160.png"

# Patcher tous les look-and-feel trouvés
# La clé wallpaper dans [Wallpaper] est "Image=" (pas "Wallpaper=")
find "$ROOTFS/usr/share/plasma/look-and-feel" -name "defaults" 2>/dev/null | while read f; do
    sed -i 's|^Image=.*|Image=ShivaOS|g' "$f" 2>/dev/null || true
    grep -q "^Image=" "$f" || echo "Image=ShivaOS" >> "$f"
done

# Script autostart wallpaper (backup si look-and-feel ignoré)
cat > "$ROOTFS/usr/local/bin/shiva-set-wallpaper.sh" << 'WALL'
#!/bin/bash
sleep 4
plasma-apply-wallpaperimage /usr/share/wallpapers/ShivaOS/contents/images/1920x1080.png 2>/dev/null || true
qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
var d = desktops(); for (var i=0; i<d.length; i++) {
    d[i].wallpaperPlugin='org.kde.image';
    d[i].currentConfigGroup=['Wallpaper','org.kde.image','General'];
    d[i].writeConfig('Image','file:///usr/share/wallpapers/ShivaOS/contents/images/1920x1080.png');
}" 2>/dev/null || true
WALL
chmod +x "$ROOTFS/usr/local/bin/shiva-set-wallpaper.sh"
mkdir -p "$ROOTFS/etc/skel/.config/autostart"
cat > "$ROOTFS/etc/skel/.config/autostart/shiva-wallpaper.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=ShivaOS Wallpaper
Exec=/usr/local/bin/shiva-set-wallpaper.sh
Terminal=false
StartupNotify=false
X-KDE-autostart-after=panel
EOF

# --- 3. SDDM — thème breeze-dark + config ---
echo "[P44] SDDM config..."
mkdir -p "$ROOTFS/etc/sddm.conf.d"
cat > "$ROOTFS/etc/sddm.conf.d/shivaos.conf" << 'EOF'
[Theme]
Current=breeze

[General]
DisplayServer=wayland
GreeterEnvironment=QT_WAYLAND_SHELL_INTEGRATION=layer-shell
EOF

# --- 4. PLYMOUTH — vérifier/fixer le thème ---
echo "[P44] Plymouth..."
if [ -d "$BRANDING/plymouth/shivaos" ]; then
    cp -r "$BRANDING/plymouth/shivaos" "$ROOTFS/usr/share/plymouth/themes/" 2>/dev/null || true
fi
# Thème par défaut = bgrt (Fedora) → on force charge ou spinner si shivaos absent
PLYMOUTH_CONF="$ROOTFS/etc/plymouth/plymouthd.conf"
mkdir -p "$(dirname "$PLYMOUTH_CONF")"
if [ -d "$ROOTFS/usr/share/plymouth/themes/shivaos" ]; then
    cat > "$PLYMOUTH_CONF" << 'EOF'
[Daemon]
Theme=shivaos
EOF
    # Lien dans initrd themes
    ln -sf /usr/share/plymouth/themes/shivaos \
        "$ROOTFS/usr/share/plymouth/themes/default.plymouth" 2>/dev/null || true
else
    cat > "$PLYMOUTH_CONF" << 'EOF'
[Daemon]
Theme=spinner
EOF
fi

# --- 5. KICKOFF LOGO ShivaOS ---
echo "[P44] Icônes Kickoff (hicolor + breeze + breeze-dark)..."
LOGO_B64=$(base64 -w0 "$BRANDING/shivaos-logo-256.png")
SVG_CONTENT="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 256 256\" width=\"256\" height=\"256\">
  <image width=\"256\" height=\"256\" xlink:href=\"data:image/png;base64,${LOGO_B64}\"/>
</svg>"

# hicolor (fallback)
for SIZE in 16 22 24 32 48 64 128 256; do
    DIR="$ROOTFS/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps"
    mkdir -p "$DIR"
    SRC="$BRANDING/shivaos-logo-256.png"
    [ -f "$BRANDING/shivaos-logo-${SIZE}.png" ] && SRC="$BRANDING/shivaos-logo-${SIZE}.png"
    cp "$SRC" "$DIR/start-here-kde.png" 2>/dev/null || true
    cp "$SRC" "$DIR/start-here.png" 2>/dev/null || true
    cp "$SRC" "$DIR/shivaos-logo.png" 2>/dev/null || true
done

# breeze + breeze-dark — KDE utilise ces SVG en priorité
for THEME in breeze breeze-dark; do
    find "$ROOTFS/usr/share/icons/$THEME/places" -name "start-here-kde.svg" -o -name "start-here-kde-plasma.svg" 2>/dev/null | while read TARGET; do
        echo "$SVG_CONTENT" > "$TARGET"
    done
done
echo "[P44] Kickoff: $(find "$ROOTFS/usr/share/icons/breeze-dark/places" -name "start-here-kde*.svg" 2>/dev/null | wc -l) SVG remplacés"

# --- 5b. PLASMA-WELCOME ShivaOS branding ---
echo "[P44] plasma-welcome branding ShivaOS..."
INTRO="$ROOTFS/usr/share/plasma/plasma-welcome/intro-customization.desktop"
if [ -f "$INTRO" ]; then
    cat > "$INTRO" << 'EOF'
[Desktop Entry]
Type=Application
Name=Welcome to ShivaOS!
Name[fr]=Bienvenue dans ShivaOS !
Name[de]=Willkommen bei ShivaOS!
Name[es]=¡Bienvenido a ShivaOS!
Name[it]=Benvenuti in ShivaOS!
Icon=/usr/share/icons/hicolor/256x256/apps/shivaos-logo.png
Comment=ShivaOS — Pure Gaming Ecosystem
URL=https://shivaos.com
EOF
fi

# --- 6. SHIVA-PULSE monitoring ---
echo "[P44] shiva-pulse..."
PULSE_SRC="/home/freuja/Documents/moi/shiva-pulse.py"
if [ -f "$PULSE_SRC" ]; then
    cp "$PULSE_SRC" "$ROOTFS/usr/share/shiva-ai/shiva-pulse.py"
    cat > "$ROOTFS/usr/lib/systemd/system/shiva-pulse.timer" << 'EOF'
[Unit]
Description=ShivaOS Pulse — monitoring timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF
    cat > "$ROOTFS/usr/lib/systemd/system/shiva-pulse.service" << 'EOF'
[Unit]
Description=ShivaOS Pulse — monitoring

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-pulse.py
EOF
    mkdir -p "$ROOTFS/etc/systemd/system/timers.target.wants"
    ln -sf /usr/lib/systemd/system/shiva-pulse.timer \
        "$ROOTFS/etc/systemd/system/timers.target.wants/shiva-pulse.timer" 2>/dev/null || true
fi

# --- 7. KDEGLOBALS couleurs ShivaOS ---
echo "[P44] KDE thème couleurs..."
cat > "$ROOTFS/etc/skel/.config/kdeglobals" << 'EOF'
[Colors:Button]
BackgroundNormal=35,20,50
DecorationFocus=224,85,0
ForegroundNormal=232,213,176
[Colors:Selection]
BackgroundNormal=200,70,0
ForegroundNormal=255,255,255
[Colors:View]
BackgroundNormal=20,12,30
DecorationFocus=224,85,0
ForegroundNormal=232,213,176
[Colors:Window]
BackgroundNormal=26,16,38
DecorationFocus=224,85,0
ForegroundNormal=232,213,176
[General]
ColorScheme=BreezeDark
widgetStyle=Breeze
[Icons]
Theme=breeze-dark
[KDE]
LookAndFeelPackage=org.kde.breezedark.desktop
EOF

# --- 8. s'assurer que python3-requests est dans le rootfs ---
# (pour que shiva marche dès le premier boot avant que DNF tourne)
echo "[P44] Vérification python3-requests..."
python3 -c "import requests" 2>/dev/null && \
    cp -r /usr/lib/python3/dist-packages/requests \
          "$ROOTFS/usr/lib/python3/site-packages/" 2>/dev/null || true

# --- 9. shiva CLI — s'assurer executable ---
chmod +x "$ROOTFS/usr/share/shiva-ai/shiva-assistant.py" 2>/dev/null || true
ln -sf /usr/share/shiva-ai/shiva-assistant.py \
    "$ROOTFS/usr/local/bin/shiva" 2>/dev/null || true

# --- 10. Recompresser EROFS ---
echo "[P44] Recompression EROFS (~5-10 min)..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -3
echo "[P44] EROFS: $(du -h "$EROFS_IMG" | cut -f1)"

# --- 11. Forge ISO ---
echo "[P44] Forge ISO ShivaOS 44..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS_IMG" /LiveOS/squashfs.img \
        -boot_image any replay 2>&1 | tail -5

# --- 12. Vérification initrd (protection anti-corruption) ---
echo "[P44] Vérification initrd..."
EXPECTED_INITRD_HASH="d820d1cd0c347a6a34617f25b4f7eb7b9662f6f7572e54eafb127710ffcd0c01"
ACTUAL_HASH=$(xorriso -osirrox on -indev "$ISO_OUT" -extract /boot/x86_64/loader/initrd /tmp/check-initrd-$$.tmp 2>/dev/null && sha256sum /tmp/check-initrd-$$.tmp | awk '{print $1}'; rm -f /tmp/check-initrd-$$.tmp)
if [ "$ACTUAL_HASH" != "$EXPECTED_INITRD_HASH" ]; then
    echo "[P44] ERREUR CRITIQUE: initrd corrompu dans l'ISO ! Hash: $ACTUAL_HASH (attendu: $EXPECTED_INITRD_HASH)"
    echo "[P44] Utilise toujours un ISO v12+ comme ISO_IN pour préserver le bon initrd."
    exit 1
fi
echo "[P44] initrd OK (hash vérifié)"

echo "[P44] === Patch terminé $(date) ==="
echo "[P44] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
