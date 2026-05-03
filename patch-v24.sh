#!/bin/bash
# Patch → v10 ISO : kernel gaming CachyOS dans first-boot
# Rebuild EROFS complet depuis le rootfs mis à jour
set -e

ROOTFS="/home/freuja/Documents/moi/BUILD_shiva44/rootfs"
EROFS_IMG="/home/freuja/Documents/moi/BUILD_shiva44/new-squashfs.img"
ISO_IN="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v9.iso"
ISO_OUT="/home/freuja/Documents/moi/ShivaOS_44_Gaming_v10.iso"

echo "[v10] Démarré $(date)"

# Recompresser EROFS depuis rootfs mis à jour
echo "[v10] Recompression EROFS (rootfs 7.8G → ~5 min)..."
rm -f "$EROFS_IMG"
mkfs.erofs -zlz4hc "$EROFS_IMG" "$ROOTFS" 2>&1 | tail -3
echo "[v10] EROFS: $(du -h "$EROFS_IMG" | cut -f1)"

# Forge ISO v10
echo "[v10] Forge ISO v10..."
xorriso -indev "$ISO_IN" \
        -outdev "$ISO_OUT" \
        -map "$EROFS_IMG" /LiveOS/squashfs.img \
        -boot_image any replay 2>&1 | tail -5

echo "[v10] === Terminé $(date) ==="
echo "[v10] ISO: $ISO_OUT — $(du -h "$ISO_OUT" | cut -f1)"
sha256sum "$ISO_OUT"
