Name:           shiva-gaming
Version:        1.2
Release:        1%{?dist}
Summary:        ShivaOS Gaming — Setup complet gaming au premier boot
License:        MIT
URL:            https://shivaos.com
BuildArch:      noarch
Requires:       shiva-core, shiva-ai, flatpak, curl, bluez, bluez-tools

%description
Meta-paquet ShivaOS Gaming : installe kernel CachyOS (BORE/ntsync),
RPM Fusion, mangohud, gamemode, lutris, mesa-vulkan, puis via Flatpak :
Steam, Discord, OBS, Bottles, Heroic, Caprine.
Bluetooth manette auto-activé au premier boot.

%prep
# no sources

%build
# no compilation

%install
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}/etc/systemd/system/multi-user.target.wants

cat > %{buildroot}/usr/local/bin/shiva-first-boot.sh << 'FIRSTBOOT'
#!/bin/bash
STAMP="/var/lib/shivaos/.first-boot-done"
[ -f "$STAMP" ] && exit 0
mkdir -p /var/lib/shivaos

REALUSER=$(getent passwd 1000 | cut -d: -f1 2>/dev/null || echo "")
[ -z "$REALUSER" ] && exit 1
USER_BUS="unix:path=/run/user/1000/bus"

_notify() {
    sudo -u "$REALUSER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="$USER_BUS" \
        notify-send "ShivaOS 44" "$1" --icon=shivaos-logo 2>/dev/null || true
}

_notify "Configuration gaming en cours... (~15 min)"

# Clé GPG ShivaOS
rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-ShivaOS 2>/dev/null || true

# RPM Fusion
dnf install -y \
    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
    "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm" \
    2>/dev/null || true

# Kernel gaming CachyOS (BORE scheduler + ntsync + futex2)
_notify "Installation kernel gaming CachyOS..."
dnf copr enable -y bieszczaders/kernel-cachyos 2>/dev/null || true
dnf install -y kernel-cachyos kernel-cachyos-headers 2>/dev/null || true
CACHYOS_VER=$(rpm -qa kernel-cachyos --queryformat '%{VERSION}-%{RELEASE}.%{ARCH}\n' 2>/dev/null | tail -1)
if [ -n "$CACHYOS_VER" ]; then
    grub2-set-default "CachyOS Linux ($CACHYOS_VER)" 2>/dev/null || true
fi

# Packages gaming + drivers GPU
_notify "Installation packages gaming..."
dnf install -y --setopt=install_weak_deps=False \
    mangohud gamemode \
    vulkan-tools mesa-vulkan-drivers mesa-dri-drivers \
    mesa-va-drivers libva-utils \
    vulkan-loader vulkan-validation-layers \
    lutris wget curl git ufw \
    python3 python3-requests \
    radeontop rocminfo \
    2>/dev/null || true

# Drivers NVIDIA si carte détectée
if lspci | grep -qi nvidia; then
    dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda 2>/dev/null || true
fi

# Flatpak + Flathub
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
_notify "Installation apps gaming (Steam, Discord, OBS...)..."
flatpak install -y --noninteractive flathub \
    com.valvesoftware.Steam \
    com.discordapp.Discord \
    com.obsproject.Studio \
    com.usebottles.bottles \
    com.heroicgameslauncher.hgl \
    com.sindresorhus.Caprine \
    2>/dev/null || true

# Bluetooth manette
_notify "Activation Bluetooth pour manettes..."
systemctl enable --now bluetooth 2>/dev/null || true
# udev : wake manettes Xbox/PS/Switch via USB sans re-plug
cat > /etc/udev/rules.d/99-shiva-gamepad.rules << 'UDEV'
# Xbox controllers
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", MODE="0666", TAG+="uaccess"
# PlayStation controllers
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", MODE="0666", TAG+="uaccess"
# Nintendo Switch Pro
SUBSYSTEM=="usb", ATTRS{idVendor}=="057e", MODE="0666", TAG+="uaccess"
# 8BitDo
SUBSYSTEM=="usb", ATTRS{idVendor}=="2dc8", MODE="0666", TAG+="uaccess"
UDEV
udevadm control --reload-rules 2>/dev/null || true

_notify "ShivaOS pret ! Kernel gaming, Steam, manettes Bluetooth/USB, Shiva AI actifs. Redemarrez pour le nouveau kernel."
touch "$STAMP"
FIRSTBOOT
chmod +x %{buildroot}/usr/local/bin/shiva-first-boot.sh

cat > %{buildroot}/usr/lib/systemd/system/shiva-first-boot.service << 'EOF'
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

ln -sf /usr/lib/systemd/system/shiva-first-boot.service \
    %{buildroot}/etc/systemd/system/multi-user.target.wants/shiva-first-boot.service

%post
systemctl daemon-reload 2>/dev/null || true
systemctl enable shiva-first-boot 2>/dev/null || true

%files
/usr/local/bin/shiva-first-boot.sh
/usr/lib/systemd/system/shiva-first-boot.service
/etc/systemd/system/multi-user.target.wants/shiva-first-boot.service

%changelog
* Sat May 02 2026 ShivaOS Team <contact@shivaos.com> - 1.2-1
- Bluetooth manette activé au premier boot (Xbox/PS/Switch/8BitDo)
- udev rules USB gamepads (mode 0666 + uaccess)
- Retiré Ollama — Shiva AI via proxy Groq uniquement

* Fri May 02 2026 ShivaOS Team <contact@shivaos.com> - 1.1-1
- Kernel gaming CachyOS (BORE/ntsync/futex2) via COPR bieszczaders/kernel-cachyos
- Notifs de progression par étape

* Thu May 01 2026 ShivaOS Team <contact@shivaos.com> - 1.0-1
- Release initiale
