#!/bin/bash
# Patch v14 → v15 : fix initial-setup.service masked → Calamares plante
# Fix : on retire le masquage /dev/null, on supprime le service proprement
# Pas de recompression EROFS — patch grub.cfg only + fix dans rootfs si dispo
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS_IMG="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v14.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v15.iso"

echo "[P44-v15] Fix initial-setup.service dans rootfs..."

# Supprimer les symlinks /dev/null (masquage) — on laisse le service exister
# Calamares peut ainsi l'activer sans erreur
rm -f "$ROOTFS/etc/systemd/system/initial-setup.service"
rm -f "$ROOTFS/etc/systemd/system/initial-setup-graphical.service"

# S'assurer qu'il n'est pas non plus dans .wants (pas activé par défaut)
rm -f "$ROOTFS/etc/systemd/system/multi-user.target.wants/initial-setup.service"
rm -f "$ROOTFS/etc/systemd/system/graphical.target.wants/initial-setup-graphical.service"

# Désactiver via plasma-welcomerc (initial-setup intégré à plasma-welcome sur Fedora KDE)
mkdir -p "$ROOTFS/etc/skel/.config"
cat > "$ROOTFS/etc/skel/.config/plasma-welcomerc" << 'EOF'
[General]
LastStartedVersion=99.0.0
ShowOnStartup=false
EOF

# Ajouter un hook post-install Calamares pour masquer initial-setup APRÈS install
# (dans la cible installée, pas dans le live)
CALAMARES_POSTINSTALL="$ROOTFS/etc/calamares/scripts"
mkdir -p "$CALAMARES_POSTINSTALL"
cat > "$CALAMARES_POSTINSTALL/99-disable-initial-setup.sh" << 'EOF'
#!/bin/bash
# Masque initial-setup dans le système installé
systemctl --root="$ROOT" mask initial-setup.service 2>/dev/null || true
systemctl --root="$ROOT" mask initial-setup-graphical.service 2>/dev/null || true
EOF
chmod +x "$CALAMARES_POSTINSTALL/99-disable-initial-setup.sh"

echo "[P44-v15] Recompression EROFS..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -3
echo "[P44-v15] EROFS: $(du -h "$EROFS_IMG" | cut -f1)"

echo "[P44-v15] Forge ISO v15..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS_IMG" /LiveOS/squashfs.img \
        -boot_image any replay 2>&1 | tail -5

echo "[P44-v15] === Terminé ==="
echo "[P44-v15] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
