#!/bin/bash
# Excalibur Center – kaldırma betiği
set -euo pipefail

if [[ $EUID -eq 0 ]]; then
    echo "[FAIL] Betiği root olarak çalıştırma." >&2
    exit 1
fi

echo "Excalibur Center kaldırılıyor..."

sudo systemctl disable --now excalibur-center-restore.service 2>/dev/null || true
sudo rm -f /lib/systemd/system/excalibur-center-restore.service
sudo systemctl daemon-reload

for ver in 1.0.0 1.1.0; do
    sudo dkms remove casper-wmi/$ver --all >/dev/null 2>&1 || true
done
sudo rmmod casper_wmi 2>/dev/null || true
sudo rm -rf /usr/src/casper-wmi-*
sudo rm -f /etc/modules-load.d/excalibur-center.conf

sudo rm -rf /opt/excalibur-center /usr/lib/excalibur-center
sudo rm -f /usr/bin/excalibur-center \
           /usr/share/applications/excalibur-center.desktop \
           /usr/share/polkit-1/actions/org.excalibur.center.policy \
           /usr/lib/udev/rules.d/99-excalibur-center.rules
sudo rm -f /usr/share/icons/hicolor/scalable/apps/excalibur-center.svg
for size in 512x512 256x256 128x128 64x64 48x48 32x32 16x16; do
    sudo rm -f "/usr/share/icons/hicolor/${size}/apps/excalibur-center.png"
done
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
sudo udevadm control --reload-rules
sudo update-desktop-database >/dev/null 2>&1 || true

echo "Tamamlandı. (~/.config/excalibur-center içindeki profillerin korunmuştur.)"
