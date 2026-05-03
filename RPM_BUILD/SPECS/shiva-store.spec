Name:           shiva-store
Version:        1.1
Release:        1%{?dist}
Summary:        ShivaOS Store — Gestionnaire d'applications gaming
License:        MIT
URL:            https://shivaos.com
BuildArch:      noarch
Source0:        shiva-store.py
Requires:       python3, python3-pyqt5, flatpak

%description
Interface graphique ShivaOS pour installer les applications gaming :
Steam, Lutris, Heroic, Bottles, OBS, Discord, Caprine, MangoHud, GameMode,
Shiva AI, Ollama, ProtonUp-Qt, Flatseal. Installation Flatpak + DNF en un clic.

%prep
# no sources

%build
# no compilation

%install
mkdir -p %{buildroot}/usr/share/shiva-store
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps

install -m755 %{_sourcedir}/shiva-store.py \
    %{buildroot}/usr/share/shiva-store/shiva-store.py

ln -sf /usr/share/shiva-store/shiva-store.py \
    %{buildroot}/usr/local/bin/shiva-store

cat > %{buildroot}/usr/share/applications/shiva-store.desktop << 'EOF'
[Desktop Entry]
Name=Shiva Store
GenericName=Gestionnaire d'applications gaming
Comment=Installer Steam, Lutris, Discord et plus
Exec=/usr/local/bin/shiva-store
Icon=shivaos-logo
Terminal=false
Type=Application
Categories=Game;System;PackageManager;
Keywords=gaming;store;steam;lutris;install;
StartupNotify=true
X-KDE-Plasma-DesktopFile-Trusted=true
EOF

%files
/usr/share/shiva-store/shiva-store.py
/usr/local/bin/shiva-store
/usr/share/applications/shiva-store.desktop

%changelog
* Fri May 02 2026 ShivaOS Team <contact@shivaos.com> - 1.1-1
- Fix : vérification is_installed() asynchrone (plus de gel UI au démarrage)
- Boutons mis à jour en background thread, fenêtre s'ouvre instantanément

* Fri May 02 2026 ShivaOS Team <contact@shivaos.com> - 1.0-1
- Release initiale Shiva Store pour Fedora 44
- Catégories Gaming / Multimédia / Outils
- Installation Flatpak + DNF en un clic
- Interface dark orange ShivaOS
