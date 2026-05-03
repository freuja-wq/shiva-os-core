Name:           shiva-core
Version:        1.0
Release:        1%{?dist}
Summary:        ShivaOS — Branding, configuration et base système
License:        MIT
URL:            https://shivaos.com
BuildArch:      noarch

%description
Branding complet ShivaOS : wallpaper, icônes Kickoff, os-release,
SDDM, désactivation KWallet et plasma-welcome, repo APT configuré.

%prep
# no sources

%build
# no compilation

%install
mkdir -p %{buildroot}

# --- os-release ---
mkdir -p %{buildroot}/etc
cat > %{buildroot}/etc/os-release << 'EOF'
NAME="ShivaOS"
VERSION="44 (Pure Gaming Ecosystem)"
ID=shivaos
ID_LIKE=fedora
VERSION_ID=44
PRETTY_NAME="ShivaOS 44 — Pure Gaming Ecosystem"
ANSI_COLOR="1;38;2;255;100;0"
HOME_URL="https://shivaos.com"
BUG_REPORT_URL="https://shivaos.com"
LOGO=shivaos-logo
EOF

# --- repo shivaos ---
mkdir -p %{buildroot}/etc/yum.repos.d
cat > %{buildroot}/etc/yum.repos.d/shivaos.repo << 'EOF'
[shivaos]
name=ShivaOS 44 — Pure Gaming Ecosystem
baseurl=https://download.copr.fedorainfracloud.org/results/freuja/ShivaOs/fedora-$releasever-$basearch/
enabled=1
gpgcheck=1
gpgkey=https://download.copr.fedorainfracloud.org/results/freuja/ShivaOs/pubkey.gpg
repo_gpgcheck=0
EOF

# --- KWallet désactivé système ---
mkdir -p %{buildroot}/etc/xdg
cat > %{buildroot}/etc/xdg/kwalletrc << 'EOF'
[Wallet]
Enabled=false
First Use=false
EOF

cat > %{buildroot}/etc/xdg/kded6rc << 'EOF'
[Module-kwalletd]
autoload=false
[Module-plasma_welcome]
autoload=false
EOF

# --- plasma-welcomerc système ---
cat > %{buildroot}/etc/xdg/plasma-welcomerc << 'EOF'
[General]
LastStartedVersion=99.0.0
ShowOnStartup=false
EOF

# --- shiva-ai.conf ---
mkdir -p %{buildroot}/etc
cat > %{buildroot}/etc/shiva-ai.conf << 'EOF'
backend=auto
groq_model=llama-3.3-70b-versatile
ollama_model=phi3:mini
EOF

# --- Wallpaper ---
mkdir -p %{buildroot}/usr/share/wallpapers/ShivaOS/contents/images
# Le fichier wallpaper est installé séparément via shiva-branding

# --- skel config ---
mkdir -p %{buildroot}/etc/skel/.config
cat > %{buildroot}/etc/skel/.config/kwalletrc << 'EOF'
[Wallet]
Enabled=false
First Use=false
EOF

cat > %{buildroot}/etc/skel/.config/kded6rc << 'EOF'
[Module-kwalletd]
autoload=false
[Module-plasma_welcome]
autoload=false
EOF

cat > %{buildroot}/etc/skel/.config/plasma-welcomerc << 'EOF'
[General]
LastStartedVersion=99.0.0
ShowOnStartup=false
EOF

%files
/etc/os-release
/etc/yum.repos.d/shivaos.repo
/etc/xdg/kwalletrc
/etc/xdg/kded6rc
/etc/xdg/plasma-welcomerc
/etc/shiva-ai.conf
/etc/skel/.config/kwalletrc
/etc/skel/.config/kded6rc
/etc/skel/.config/plasma-welcomerc

%changelog
* Thu May 01 2026 ShivaOS Team <contact@shivaos.com> - 1.0-1
- Release initiale ShivaOS 44
