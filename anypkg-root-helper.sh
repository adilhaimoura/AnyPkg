#!/usr/bin/env bash
# Privileged Polkit helper for AnyPkg (invoked via pkexec across Arch, Debian/Ubuntu/Mint, and Fedora/openSUSE)
set -euo pipefail

ACTION="${1:-}"
ARG="${2:-}"

detect_base() {
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

BASE="$(detect_base)"

case "$ACTION" in
    update-db)
        echo "==> Updating package & library lookup databases for host ($BASE)..."
        case "$BASE" in
            arch)
                if command -v pkgfile >/dev/null 2>&1; then
                    pkgfile -u || true
                fi
                if command -v debtap >/dev/null 2>&1; then
                    debtap -u
                fi
                ;;
            deb)
                apt-get update
                if command -v apt-file >/dev/null 2>&1; then
                    apt-file update || true
                fi
                ;;
            dnf)
                dnf makecache || true
                ;;
            zypper)
                zypper --non-interactive refresh || true
                ;;
        esac
        echo "==> Database update complete."
        ;;
    install-pkg)
        if [[ -z "$ARG" || ! -f "$ARG" ]]; then
            echo "Error: Package file not found: $ARG" >&2
            exit 1
        fi
        echo "==> Installing native package and dependencies ($ARG)..."
        case "$BASE" in
            arch)
                pacman -U --noconfirm --needed "$ARG"
                ;;
            deb)
                DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades "$ARG"
                ;;
            dnf)
                dnf install -y "$ARG"
                ;;
            zypper)
                zypper --non-interactive install --allow-unsigned-rpm "$ARG"
                ;;
            *)
                echo "Error: Unsupported host package manager." >&2
                exit 1
                ;;
        esac
        echo "==> Native installation finished successfully!"
        ;;
    *)
        echo "Usage: $0 {update-db|install-pkg <pkg_path>}" >&2
        exit 2
        ;;
esac
