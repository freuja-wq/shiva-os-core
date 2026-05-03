Name:           shiva-ai
Version:        1.0
Release:        1%{?dist}
Summary:        ShivaOS AI — 10 modules d'intelligence gaming
License:        MIT
URL:            https://shivaos.com
BuildArch:      noarch
Requires:       python3, python3-requests, shiva-core

%description
10 modules Python pour l'IA ShivaOS : assistant, repair, gaming optimizer,
thermal guard, fps coach, bug detector, hardware probe, session report,
compatibility scout, update oracle. CLI : commande 'shiva'.

%prep
# no sources

%build
# no compilation

%install
mkdir -p %{buildroot}/usr/share/shiva-ai
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}/etc/systemd/system/multi-user.target.wants
mkdir -p %{buildroot}/etc/systemd/system/timers.target.wants

# Copier les modules Python (depuis les sources)
for f in shiva-assistant shiva-repair shiva-gaming-optimizer shiva-bug-detector \
          shiva-fps-coach shiva-thermal-guard shiva-update-oracle \
          shiva-compatibility-scout shiva-session-report shiva-hardware-probe shiva-pulse; do
    [ -f %{_sourcedir}/${f}.py ] && install -m755 %{_sourcedir}/${f}.py \
        %{buildroot}/usr/share/shiva-ai/${f}.py
done

# CLI shiva
ln -sf /usr/share/shiva-ai/shiva-assistant.py %{buildroot}/usr/local/bin/shiva

# Desktop entry
mkdir -p %{buildroot}/usr/share/applications
cat > %{buildroot}/usr/share/applications/shiva-ai.desktop << 'EOF'
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

# Services systemd
cat > %{buildroot}/usr/lib/systemd/system/shiva-repair.service << 'EOF'
[Unit]
Description=ShivaOS Auto-Repair
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-repair.py
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

cat > %{buildroot}/usr/lib/systemd/system/shiva-gaming-optimizer.service << 'EOF'
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

cat > %{buildroot}/usr/lib/systemd/system/shiva-thermal-guard.service << 'EOF'
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

cat > %{buildroot}/usr/lib/systemd/system/shiva-hardware-probe.service << 'EOF'
[Unit]
Description=ShivaOS Hardware Probe
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

cat > %{buildroot}/usr/lib/systemd/system/shiva-pulse.service << 'EOF'
[Unit]
Description=ShivaOS Pulse — monitoring

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-pulse.py
EOF

cat > %{buildroot}/usr/lib/systemd/system/shiva-pulse.timer << 'EOF'
[Unit]
Description=ShivaOS Pulse — timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

cat > %{buildroot}/usr/lib/systemd/system/shiva-update-oracle.service << 'EOF'
[Unit]
Description=ShivaOS Update Oracle — vérification mises à jour approuvées

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/share/shiva-ai/shiva-update-oracle.py
User=root
EOF

cat > %{buildroot}/usr/lib/systemd/system/shiva-update-oracle.timer << 'EOF'
[Unit]
Description=ShivaOS Update Oracle — timer 5min

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# Activer les services via symlinks
ln -sf /usr/lib/systemd/system/shiva-repair.service \
    %{buildroot}/etc/systemd/system/multi-user.target.wants/shiva-repair.service
ln -sf /usr/lib/systemd/system/shiva-gaming-optimizer.service \
    %{buildroot}/etc/systemd/system/multi-user.target.wants/shiva-gaming-optimizer.service
ln -sf /usr/lib/systemd/system/shiva-thermal-guard.service \
    %{buildroot}/etc/systemd/system/multi-user.target.wants/shiva-thermal-guard.service
ln -sf /usr/lib/systemd/system/shiva-hardware-probe.service \
    %{buildroot}/etc/systemd/system/multi-user.target.wants/shiva-hardware-probe.service
ln -sf /usr/lib/systemd/system/shiva-pulse.timer \
    %{buildroot}/etc/systemd/system/timers.target.wants/shiva-pulse.timer
ln -sf /usr/lib/systemd/system/shiva-update-oracle.timer \
    %{buildroot}/etc/systemd/system/timers.target.wants/shiva-update-oracle.timer

%post
systemctl daemon-reload 2>/dev/null || true
systemctl enable --now shiva-repair shiva-gaming-optimizer shiva-thermal-guard shiva-hardware-probe shiva-pulse.timer shiva-update-oracle.timer 2>/dev/null || true

%files
/usr/share/shiva-ai/
/usr/local/bin/shiva
/usr/share/applications/shiva-ai.desktop
/usr/lib/systemd/system/shiva-*.service
/usr/lib/systemd/system/shiva-pulse.timer
/usr/lib/systemd/system/shiva-update-oracle.timer
/etc/systemd/system/multi-user.target.wants/shiva-*.service
/etc/systemd/system/timers.target.wants/shiva-pulse.timer
/etc/systemd/system/timers.target.wants/shiva-update-oracle.timer

%changelog
* Thu May 01 2026 ShivaOS Team <contact@shivaos.com> - 1.0-1
- Release initiale
