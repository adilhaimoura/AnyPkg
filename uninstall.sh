#!/usr/bin/env bash
set -euo pipefail

echo "==> Removing AnyPkg system files..."
sudo rm -f /usr/local/bin/anypkg
sudo rm -f /usr/local/bin/anypkg-root-helper
sudo rm -f /usr/share/polkit-1/actions/org.anypkg.policy
sudo rm -f /usr/share/applications/anypkg.desktop
sudo rm -f /etc/anypkg.conf
sudo update-desktop-database /usr/share/applications || true
echo "==> AnyPkg uninstalled successfully."
