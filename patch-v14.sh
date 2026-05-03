#!/bin/bash
# Patch v13 → v14 : désactive SELinux dans le GRUB (selinux=0)
# Pas de recompression EROFS — patch grub.cfg uniquement
set -e

ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v13.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v14.iso"
GRUB_TMP="/tmp/shiva44-grub-v14.cfg"

echo "[P44-v14] Extraction grub.cfg..."
xorriso -osirrox on -indev "$ISO_IN" \
    -extract /boot/grub2/grub.cfg "$GRUB_TMP" 2>/dev/null

echo "[P44-v14] Ajout selinux=0 + enforcing=0..."
# Ajoute selinux=0 sur toutes les lignes linux (kernel cmdline)
sed -i 's|\(linux .*rd\.live\.image\)|\1 selinux=0 enforcing=0|g' "$GRUB_TMP"

echo "[P44-v14] Nouveau grub.cfg :"
cat "$GRUB_TMP"

echo ""
echo "[P44-v14] Forge ISO v14..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$GRUB_TMP" /boot/grub2/grub.cfg \
        -boot_image any replay 2>&1 | tail -5

echo "[P44-v14] === Terminé ==="
echo "[P44-v14] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
