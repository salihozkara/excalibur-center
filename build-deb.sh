#!/bin/bash
# Excalibur Center – .deb paketi oluşturur
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.0.1"
PKG="excalibur-center_${VERSION}_amd64"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

echo "── Paket yapısı hazırlanıyor..."

# DEBIAN
mkdir -p "$BUILD/$PKG/DEBIAN"

cat > "$BUILD/$PKG/DEBIAN/control" <<EOF
Package: excalibur-center
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3 (>=3.10), python3-pyqt6, dkms, build-essential, polkitd | policykit-1
Recommends: linux-headers-generic
Suggests: smartmontools
Installed-Size: 25000
Maintainer: SALİH ÖZKARA <58659931+salihozkara@users.noreply.github.com>
Description: Unofficial Control Center for Casper Excalibur laptops
 Keyboard RGB zone lighting, power plans and fan monitoring for
 Casper Excalibur laptops via the casper-wmi kernel interface.
 Includes DKMS-built casper-wmi driver (v1.1.0 fork with G770 fixes).
Homepage: https://github.com/salihozkara/excalibur-center
EOF

cat > "$BUILD/$PKG/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
KVER="$(uname -r)"

# DKMS modülü (başlıklar varsa)
if [ -d "/usr/src/casper-wmi-1.1.0" ]; then
    if [ -d "/lib/modules/$KVER/build" ]; then
        dkms add -m casper-wmi -v 1.1.0 >/dev/null 2>&1 || true
        dkms build -m casper-wmi -v 1.1.0 >/dev/null 2>&1 && \
        dkms install -m casper-wmi -v 1.1.0 >/dev/null 2>&1 || \
            echo "UYARI: DKMS derlemesi başarısız (linux-headers-$KVER gerekli)." >&2
    else
        echo "UYARI: linux-headers-$KVER yok; kurup 'sudo dkms install casper-wmi/1.1.0' çalıştırın." >&2
    fi
fi

echo "casper_wmi" > /etc/modules-load.d/excalibur-center.conf
modprobe casper_wmi 2>/dev/null || true

LED="/sys/class/leds/casper::kbd_backlight/led_control"
if [ -e "$LED" ]; then
    chgrp video "$LED" 2>/dev/null || true
    chmod 0660 "$LED" 2>/dev/null || true
fi

udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

systemctl daemon-reload 2>/dev/null || true
systemctl enable excalibur-center-restore.service 2>/dev/null || true

# video grubuna ekle (ilk kullanıcı)
FIRST_USER="$(getent passwd 1000 | cut -d: -f1)"
if [ -n "$FIRST_USER" ] && ! id -nG "$FIRST_USER" | grep -qw video; then
    usermod -aG video "$FIRST_USER" 2>/dev/null || true
    echo "NOT: '$FIRST_USER' video grubuna eklendi; etkisi için yeniden oturum açın."
fi

gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
echo "Excalibur Center kuruldu. Menüden açabilirsiniz: excalibur-center"
EOF

cat > "$BUILD/$PKG/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
systemctl disable --now excalibur-center-restore.service 2>/dev/null || true
rmmod casper_wmi 2>/dev/null || true
exit 0
EOF

cat > "$BUILD/$PKG/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e
dkms remove casper-wmi/1.1.0 --all >/dev/null 2>&1 || true
rm -f /etc/modules-load.d/excalibur-center.conf
depmod -a 2>/dev/null || true
exit 0
EOF

chmod 755 "$BUILD/$PKG/DEBIAN"/postinst "$BUILD/$PKG/DEBIAN"/prerm "$BUILD/$PKG/DEBIAN"/postrm

# Uygulama
mkdir -p "$BUILD/$PKG/opt/excalibur-center"
cp -r "$REPO/excalibur_center" "$BUILD/$PKG/opt/excalibur-center/"
find "$BUILD/$PKG/opt" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# Sistem dosyaları
mkdir -p "$BUILD/$PKG/usr/bin" \
         "$BUILD/$PKG/usr/lib/excalibur-center" \
         "$BUILD/$PKG/usr/share/applications" \
         "$BUILD/$PKG/usr/share/polkit-1/actions" \
         "$BUILD/$PKG/usr/lib/udev/rules.d" \
         "$BUILD/$PKG/lib/systemd/system" \
         "$BUILD/$PKG/usr/src/casper-wmi-1.1.0"

cat > "$BUILD/$PKG/usr/bin/excalibur-center" <<'EOF'
#!/bin/bash
cd /opt/excalibur-center
exec /usr/bin/python3 -m excalibur_center.cli "$@"
EOF
chmod 755 "$BUILD/$PKG/usr/bin/excalibur-center"

install -m755 "$REPO/data/priv-write-helper" "$BUILD/$PKG/usr/lib/excalibur-center/priv-write-helper"
install -m644 "$REPO/data/excalibur-center.desktop" "$BUILD/$PKG/usr/share/applications/"
install -m644 "$REPO/data/org.excalibur.center.policy" "$BUILD/$PKG/usr/share/polkit-1/actions/"
install -m644 "$REPO/data/99-excalibur-center.rules" "$BUILD/$PKG/usr/lib/udev/rules.d/"
install -m644 "$REPO/systemd/excalibur-center-restore.service" "$BUILD/$PKG/lib/systemd/system/"

cp "$REPO/driver/casper-wmi.c" "$REPO/driver/Makefile" "$REPO/driver/dkms.conf" \
   "$BUILD/$PKG/usr/src/casper-wmi-1.1.0/"

# İkonlar
for size in 512 256 128 64 48 32 16; do
    d="$BUILD/$PKG/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$d"
    cp "$REPO/assets/icons/$size/excalibur-center.png" "$d/"
done
mkdir -p "$BUILD/$PKG/usr/share/icons/hicolor/scalable/apps"
cp "$REPO/assets/excalibur-center.svg" "$BUILD/$PKG/usr/share/icons/hicolor/scalable/apps/"

# Sürüm dosyası
mkdir -p "$BUILD/$PKG/usr/share/doc/excalibur-center"
cp "$REPO/README.md" "$REPO/CHANGELOG.md" "$REPO/LICENSE" "$BUILD/$PKG/usr/share/doc/excalibur-center/"

echo "── .deb oluşturuluyor..."
mkdir -p "$REPO/dist"
dpkg-deb --build --root-owner-group "$BUILD/$PKG" "$REPO/dist/$PKG.deb"
ls -lh "$REPO/dist/"
