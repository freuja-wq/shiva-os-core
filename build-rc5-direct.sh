#!/bin/bash
# RC5 — ISO complète : tout dedans, zero download post-install
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_RC4.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_RC5.iso"
AI_SRC="/home/freuja/Documents/moi/SHIVA_GENESIS/scripts/shiva-ai"
STORE_SRC="/home/freuja/Documents/moi/SHIVA_GENESIS/scripts/shiva-store.py"
PULSE_SRC="/home/freuja/Documents/moi/shiva-pulse.py"

echo "[RC5] === Direct Install Build complet $(date) ==="

# ── 1. Monter le chroot ──────────────────────────────────────────────────────
echo "[RC5] Montage chroot..."
mount --bind /dev     "$ROOTFS/dev"
mount --bind /dev/pts "$ROOTFS/dev/pts"
mount -t proc  proc   "$ROOTFS/proc"
mount -t sysfs sysfs  "$ROOTFS/sys"
mount -t tmpfs tmpfs  "$ROOTFS/run"
cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf"

cleanup() {
    echo "[RC5] Démontage chroot..."
    umount -lf "$ROOTFS/dev/pts" 2>/dev/null || true
    umount -lf "$ROOTFS/dev"     2>/dev/null || true
    umount -lf "$ROOTFS/proc"    2>/dev/null || true
    umount -lf "$ROOTFS/sys"     2>/dev/null || true
    umount -lf "$ROOTFS/run"     2>/dev/null || true
}
trap cleanup EXIT

# ── 2. Packages gaming — déjà dans le rootfs (mangohud, gamemode, lutris, flatpak, vulkan)
echo "[RC5] Packages gaming déjà présents — skip dnf"

# ── 3. Flatpak apps — installées depuis l'hôte dans le rootfs ───────────────
echo "[RC5] Ajout Flathub dans rootfs..."
FLATPAK_INST="$ROOTFS/var/lib/flatpak"
mkdir -p "$FLATPAK_INST"
flatpak --installation="$FLATPAK_INST" remote-add --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true

echo "[RC5] Installation Flatpak apps (~30-60 min)..."
for app in \
    com.valvesoftware.Steam \
    com.discordapp.Discord \
    com.obsproject.Studio \
    com.usebottles.bottles \
    com.heroicgameslauncher.hgl; do
    echo "[RC5]   → $app"
    flatpak --installation="$FLATPAK_INST" install -y flathub "$app" 2>&1 | tail -3 || true
done
echo "[RC5] Flatpak apps OK"

# ── 4. Copier Shiva AI (10 modules + mode détente) ───────────────────────────
echo "[RC5] Copie Shiva AI..."
mkdir -p "$ROOTFS/usr/share/shiva-ai"
cp "$AI_SRC"/*.py "$ROOTFS/usr/share/shiva-ai/"
cp "$PULSE_SRC" "$ROOTFS/usr/share/shiva-ai/shiva-pulse.py"
chmod +x "$ROOTFS/usr/share/shiva-ai/"*.py
ln -sf /usr/share/shiva-ai/shiva-assistant.py "$ROOTFS/usr/local/bin/shiva"

# ── 5. Copier Shiva Store + icône bureau ────────────────────────────────────
echo "[RC5] Copie Shiva Store..."
mkdir -p "$ROOTFS/usr/share/shiva-store"
cp "$STORE_SRC" "$ROOTFS/usr/share/shiva-store/shiva-store.py"
chmod +x "$ROOTFS/usr/share/shiva-store/shiva-store.py"
ln -sf /usr/share/shiva-store/shiva-store.py "$ROOTFS/usr/local/bin/shiva-store"

# Icône bureau + skel (présente sur le bureau de tous les nouveaux users)
cat > "$ROOTFS/usr/share/applications/shiva-store.desktop" << 'EOF'
[Desktop Entry]
Name=Shiva Store
Comment=Catalogue gaming ShivaOS
Exec=firefox https://shivaos.com/store.php
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;
X-KDE-Plasma-DesktopFile-Trusted=true
EOF

mkdir -p "$ROOTFS/etc/skel/Desktop"
cp "$ROOTFS/usr/share/applications/shiva-store.desktop" "$ROOTFS/etc/skel/Desktop/shiva-store.desktop"
chmod +x "$ROOTFS/etc/skel/Desktop/shiva-store.desktop"

# ── 6. Services systemd Shiva AI ─────────────────────────────────────────────
echo "[RC5] Services systemd..."
cat > "$ROOTFS/usr/lib/systemd/system/shiva-repair.service" << 'EOF'
[Unit]
Description=ShivaOS Auto-Repair 24/7
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-repair.py
Restart=on-failure
User=root
[Install]
WantedBy=multi-user.target
EOF

cat > "$ROOTFS/usr/lib/systemd/system/shiva-gaming-optimizer.service" << 'EOF'
[Unit]
Description=ShivaOS Gaming Optimizer
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-gaming-optimizer.py
Restart=on-failure
User=root
[Install]
WantedBy=multi-user.target
EOF

cat > "$ROOTFS/usr/lib/systemd/system/shiva-thermal-guard.service" << 'EOF'
[Unit]
Description=ShivaOS Thermal Guard
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-thermal-guard.py
Restart=on-failure
User=root
[Install]
WantedBy=multi-user.target
EOF

cat > "$ROOTFS/usr/lib/systemd/system/shiva-hardware-probe.service" << 'EOF'
[Unit]
Description=ShivaOS Hardware Probe (one-shot)
After=network.target
ConditionPathExists=!/etc/shiva-hardware.json
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-hardware-probe.py
RemainAfterExit=yes
User=root
[Install]
WantedBy=multi-user.target
EOF

mkdir -p "$ROOTFS/etc/systemd/system/multi-user.target.wants"
for svc in shiva-repair shiva-gaming-optimizer shiva-thermal-guard shiva-hardware-probe; do
    ln -sf "/usr/lib/systemd/system/$svc.service" \
        "$ROOTFS/etc/systemd/system/multi-user.target.wants/$svc.service" 2>/dev/null || true
done

# ── 7. First-boot minimal (stamp seulement, rien à faire) ────────────────────
echo "[RC5] First-boot minimal..."
cat > "$ROOTFS/usr/local/bin/shiva-first-boot.sh" << 'FIRSTBOOT'
#!/bin/bash
# ShivaOS — tout est déjà dans l'ISO
STAMP="/var/lib/shiva-first-boot-done"
[ -f "$STAMP" ] && exit 0

REALUSER=$(getent passwd 1000 | cut -d: -f1 2>/dev/null || echo "")
USER_BUS="unix:path=/run/user/1000/bus"
_notify() {
    sudo -u "$REALUSER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="$USER_BUS" \
        notify-send "ShivaOS 44" "$1" --icon=shivaos-logo 2>/dev/null || true
}

_notify "🔱 Bienvenue sur ShivaOS 44 — Pure Gaming Ecosystem"
touch "$STAMP"
FIRSTBOOT
chmod +x "$ROOTFS/usr/local/bin/shiva-first-boot.sh"

cat > "$ROOTFS/usr/lib/systemd/system/shiva-first-boot.service" << 'EOF'
[Unit]
Description=ShivaOS First Boot Welcome
After=graphical.target
ConditionPathExists=!/var/lib/shiva-first-boot-done
[Service]
Type=oneshot
ExecStart=/usr/local/bin/shiva-first-boot.sh
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF

ln -sf /usr/lib/systemd/system/shiva-first-boot.service \
    "$ROOTFS/etc/systemd/system/multi-user.target.wants/shiva-first-boot.service" 2>/dev/null || true

# ── 8. Fix xattrs SELinux sur TOUS les nouveaux fichiers ─────────────────────
echo "[RC5] Fix xattrs SELinux..."

_xattr_usr() {
    setfattr -n security.selinux -v "system_u:object_r:usr_t:s0" "$1" 2>/dev/null || true
}
_xattr_bin() {
    setfattr -n security.selinux -v "system_u:object_r:bin_t:s0" "$1" 2>/dev/null || true
}
_xattr_svc() {
    setfattr -n security.selinux -v "system_u:object_r:systemd_unit_file_t:s0" "$1" 2>/dev/null || true
}

# Modules Shiva AI
find "$ROOTFS/usr/share/shiva-ai"  \( -type f -o -type l \) | while read f; do _xattr_usr "$f"; done

# Shiva Store
find "$ROOTFS/usr/share/shiva-store" \( -type f -o -type l \) | while read f; do _xattr_usr "$f"; done

# Binaires /usr/local/bin (bin_t)
for f in "$ROOTFS/usr/local/bin/shiva" \
         "$ROOTFS/usr/local/bin/shiva-store" \
         "$ROOTFS/usr/local/bin/shiva-first-boot.sh"; do
    [ -e "$f" ] && _xattr_bin "$f"
done

# Desktop files
for f in "$ROOTFS/usr/share/applications/shiva-store.desktop" \
         "$ROOTFS/etc/skel/Desktop/shiva-store.desktop"; do
    [ -e "$f" ] && _xattr_usr "$f"
done

# Répertoire skel Desktop
[ -d "$ROOTFS/etc/skel/Desktop" ] && _xattr_usr "$ROOTFS/etc/skel/Desktop"

# Services systemd (fichiers .service)
for svc in shiva-repair shiva-gaming-optimizer shiva-thermal-guard \
           shiva-hardware-probe shiva-first-boot; do
    f="$ROOTFS/usr/lib/systemd/system/$svc.service"
    [ -f "$f" ] && _xattr_svc "$f"
done

# Symlinks .target.wants (contexte systemd_unit_file_t)
for f in "$ROOTFS/etc/systemd/system/multi-user.target.wants"/shiva-*.service; do
    [ -e "$f" ] && _xattr_svc "$f"
done

echo "[RC5] xattrs OK"

# ── 9. Nettoyage ─────────────────────────────────────────────────────────────
rm -f "$ROOTFS/etc/yum.repos.d/shivaos.repo"
rm -f "$ROOTFS/etc/resolv.conf"

echo "[RC5] Démontage..."
cleanup
trap - EXIT

# ── 10. Rebuild EROFS ────────────────────────────────────────────────────────
echo "[RC5] Rebuild EROFS (~15 min)..."
rm -f "$EROFS"
mkfs.erofs -zlz4hc "$EROFS" "$ROOTFS"
echo "[RC5] EROFS: $(du -h "$EROFS" | cut -f1)"

# ── 11. Forge ISO ────────────────────────────────────────────────────────────
echo "[RC5] Forge ISO RC5..."
rm -f "$ISO_OUT"
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS" /LiveOS/squashfs.img \
        -boot_image any replay

echo "[RC5] === Terminé $(date) ==="
echo "[RC5] ISO: $ISO_OUT"
echo "[RC5] Taille: $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
