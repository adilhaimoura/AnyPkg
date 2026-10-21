#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================================="
echo "  AnyPkg — Universal Native Linux Package Converter & Installer"
echo "  Supports: Arch Base (.pkg.tar.zst) | Debian/Mint (.deb) | Fedora/openSUSE (.rpm)"
echo "================================================================="

if [[ $EUID -eq 0 ]]; then
    echo "Please run ./install.sh as your normal user (not root)."
    echo "It will prompt for sudo when needed."
    exit 1
fi

detect_host_base() {
    if command -v pacman >/dev/null 2>&1; then
        echo "arch"
    elif command -v apt-get >/dev/null 2>&1; then
        echo "deb"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

install_yay_from_aur() {
    echo "==> Building and installing 'yay' (yay-bin) from AUR..."
    sudo pacman -S --needed --noconfirm git base-devel
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    git clone https://aur.archlinux.org/yay-bin.git "$tmp_dir/yay-bin"
    (cd "$tmp_dir/yay-bin" && makepkg -si --noconfirm)
    rm -rf "$tmp_dir"
}

HOST_BASE="$(detect_host_base)"
PRETTY_OS="$(grep -E '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "Linux")"
AUR_HELPER="pacman_only"

echo "==> Detected System: $PRETTY_OS (Base: $HOST_BASE)"
echo ""

case "$HOST_BASE" in
    arch)
        echo "Which AUR helper do you use (for setting up debtap and resolving AUR dependencies)?"
        echo "  1) yay"
        echo "  2) paru"
        echo "  3) none (pacman only)"
        read -r -p "Select an option [1-3] (default: 1): " aur_choice
        aur_choice="${aur_choice:-1}"

        case "$aur_choice" in
            1|yay)
                if command -v yay >/dev/null 2>&1; then
                    AUR_HELPER="yay"
                else
                    read -r -p "'yay' is not installed yet. Install 'yay' automatically now? [Y/n]: " inst_yay
                    inst_yay="${inst_yay:-Y}"
                    if [[ "$inst_yay" =~ ^[Yy] ]]; then
                        install_yay_from_aur
                        AUR_HELPER="yay"
                    fi
                fi
                ;;
            2|paru)
                if command -v paru >/dev/null 2>&1; then
                    AUR_HELPER="paru"
                else
                    read -r -p "'paru' is not installed. Would you like to install 'yay' instead? [Y/n]: " inst_yay
                    inst_yay="${inst_yay:-Y}"
                    if [[ "$inst_yay" =~ ^[Yy] ]]; then
                        install_yay_from_aur
                        AUR_HELPER="yay"
                    fi
                fi
                ;;
            *)
                read -r -p "No AUR helper selected. Would you like to install 'yay' so AnyPkg can auto-install AUR dependencies? [Y/n]: " inst_yay
                inst_yay="${inst_yay:-Y}"
                if [[ "$inst_yay" =~ ^[Yy] ]]; then
                    install_yay_from_aur
                    AUR_HELPER="yay"
                else
                    AUR_HELPER="pacman_only"
                fi
                ;;
        esac

        echo "==> [1/4] Installing required Arch Linux packages via pacman..."
        sudo pacman -S --needed --noconfirm \
            python python-gobject gtk4 libadwaita polkit \
            pkgfile fakeroot binutils libarchive zstd squashfs-tools rpm-tools \
            desktop-file-utils shared-mime-info xdg-utils

        echo "==> [2/4] Ensuring 'debtap' is installed..."
        if ! command -v debtap >/dev/null 2>&1; then
            if [[ "$AUR_HELPER" == "yay" || "$AUR_HELPER" == "paru" ]] && command -v "$AUR_HELPER" >/dev/null 2>&1; then
                "$AUR_HELPER" -S --needed --noconfirm debtap
            else
                sudo pacman -S --needed --noconfirm git base-devel
                tmp_aur="$(mktemp -d)"
                git clone https://aur.archlinux.org/debtap.git "$tmp_aur/debtap"
                (cd "$tmp_aur/debtap" && makepkg -si --noconfirm)
                rm -rf "$tmp_aur"
            fi
        fi

        echo "==> Initializing pkgfile & debtap databases if needed..."
        if [[ ! -d /var/cache/debtap ]] || [[ -z "$(ls -A /var/cache/debtap 2>/dev/null || true)" ]]; then
            sudo pkgfile -u || true
            sudo debtap -u
        fi
        ;;

    deb)
        echo "==> [1/4] Installing required Debian / Ubuntu / Linux Mint packages via apt..."
        sudo apt-get update
        sudo apt-get install -y \
            python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 policykit-1 \
            libarchive-tools fakeroot binutils dpkg-dev zstd squashfs-tools apt-file rpm \
            desktop-file-utils shared-mime-info xdg-utils
        echo "==> [2/4] Updating apt-file database..."
        sudo apt-file update || true
        ;;

    dnf)
        echo "==> [1/4] Installing required Fedora / RHEL packages via dnf..."
        sudo dnf install -y \
            python3 python3-gobject gtk4 libadwaita polkit \
            bsdtar fakeroot binutils rpm-build zstd squashfs-tools dpkg \
            desktop-file-utils shared-mime-info xdg-utils
        ;;

    zypper)
        echo "==> [1/4] Installing required openSUSE packages via zypper..."
        sudo zypper --non-interactive install \
            python3 python3-gobject typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 polkit \
            bsdtar fakeroot binutils rpm-build zstd squashfs dpkg \
            desktop-file-utils shared-mime-info xdg-utils
        ;;

    *)
        echo "Error: Unsupported Linux distribution (could not find pacman, apt-get, dnf, or zypper)."
        exit 1
        ;;
esac

echo "==> [3/4] Installing AnyPkg binaries, Polkit policy, system config, and Desktop launcher..."
sudo install -Dm755 "$SCRIPT_DIR/anypkg.py" /usr/local/bin/anypkg
sudo install -Dm755 "$SCRIPT_DIR/anypkg-root-helper.sh" /usr/local/bin/anypkg-root-helper
sudo install -Dm644 "$SCRIPT_DIR/org.anypkg.policy" /usr/share/polkit-1/actions/org.anypkg.policy
sudo install -Dm644 "$SCRIPT_DIR/anypkg.desktop" /usr/share/applications/anypkg.desktop

sudo tee /etc/anypkg.conf >/dev/null <<EOF
{
  "aur_helper": "$AUR_HELPER"
}
EOF

echo "==> [4/4] Registering AnyPkg as the default double-click handler for Linux packages..."
sudo update-desktop-database /usr/share/applications || true
for mime in \
    application/vnd.debian.binary-package \
    application/x-deb \
    application/x-debian-package \
    application/x-rpm \
    application/x-redhat-package-manager \
    application/vnd.appimage \
    application/x-iso9660-appimage \
    application/vnd.snap; do
    xdg-mime default anypkg.desktop "$mime" || true
done

echo ""
echo "================================================================="
echo "  ✓ AnyPkg Installed Successfully on $PRETTY_OS!"
echo "================================================================="
echo "Launch from your Application Menu ('AnyPkg'), double-click any"
echo "Linux package file, or run: anypkg /path/to/package"
