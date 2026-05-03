#!/bin/bash
# Patch v16 → v17 : grub.cfg only (pas de recompression EROFS)
# Fixes: plasma-welcome supprimé, xwaylandvideobridge supprimé
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS_IMG="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v16.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v17.iso"

echo "[P44-v17] Suppression plasma-welcome + xwaylandvideobridge..."

# Supprimer plasma-welcome partout
for f in \
    "$ROOTFS/etc/xdg/autostart/org.kde.welcome.desktop" \
    "$ROOTFS/etc/xdg/autostart/plasma-welcome.desktop" \
    "$ROOTFS/usr/share/autostart/org.kde.welcome.desktop" \
    "$ROOTFS/usr/share/autostart/plasma-welcome.desktop"; do
    [ -f "$f" ] && rm -f "$f" && echo "  Supprimé: $f"
done

# Supprimer xwaylandvideobridge (plante en VM, inutile)
rm -f "$ROOTFS/etc/xdg/autostart/org.kde.xwaylandvideobridge.desktop"
echo "  Supprimé: xwaylandvideobridge"

# Recompresser EROFS
echo "[P44-v17] Recompression EROFS..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -3
echo "[P44-v17] EROFS: $(du -h "$EROFS_IMG" | cut -f1)"

# Forge ISO
echo "[P44-v17] Forge ISO v17..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS_IMG" /LiveOS/squashfs.img \
        -boot_image any replay 2>&1 | tail -5

echo "[P44-v17] === Terminé $(date) ==="
echo "[P44-v17] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
