#!/bin/bash
# Excalibur Center – Debian/Ubuntu/Mint kurulum betiği
set -euo pipefail

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; CYAN=$'\033[0;36m'; NC=$'\033[0m'
info() { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK ]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Kaynak kontrolü: depo değilse GitHub'dan indir ───────────
# curl | bash ile çalıştırıldığında dosyalar yerelde olmaz;
# master dalının arşivini indirip oradan devam eder.
if [[ ! -f "${SCRIPT_DIR}/driver/casper-wmi.c" || ! -d "${SCRIPT_DIR}/excalibur_center" ]]; then
    info "Kaynak dosyalar yerelde yok — GitHub'dan indiriliyor..."
    DL="$(mktemp -d)"
    trap 'rm -rf "$DL"' EXIT
    curl -fsSL "https://github.com/salihozkara/excalibur-center/archive/refs/heads/master.tar.gz" \
        | tar -xz -C "$DL" || fail "İndirme başarısız. İnternet bağlantını kontrol et."
    SCRIPT_DIR="$(echo "$DL"/*/)"/.
    ok "Kaynak hazır."
fi

if [[ $EUID -eq 0 ]]; then
    fail "Betiği root olarak çalıştırma; gerektiğinde sudo kullanacak."
fi

echo ""
echo "════════════════════════════════════════════"
echo "  Excalibur Center – Kurulum (Debian/Mint)"
echo "════════════════════════════════════════════"
echo ""

# ── 1. Bağımlılıklar ─────────────────────────────────────────
info "Bağımlılıklar kontrol ediliyor..."
DEPS=(python3 python3-pyqt6 dkms build-essential)
MISSING=()
for dep in "${DEPS[@]}"; do
    dpkg -s "$dep" &>/dev/null || MISSING+=("$dep")
done
KVER="$(uname -r)"
dpkg -s "linux-headers-${KVER}" &>/dev/null || MISSING+=("linux-headers-${KVER}")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    info "Kuruluyor: ${MISSING[*]}"
    sudo apt-get update -qq || true
    sudo apt-get install -y "${MISSING[@]}"
fi
ok "Bağımlılıklar hazır."

# ── 2. casper-wmi çekirdek modülü (DKMS) ─────────────────────
DRIVER_VER="1.1.0"
SRC="/usr/src/casper-wmi-${DRIVER_VER}"

if lsmod | grep -q '^casper_wmi '; then
    info "Yüklü modül kaldırılıyor (yeni sürüm kurulacak)..."
    sudo rmmod casper_wmi 2>/dev/null || \
        fail "casper_wmi kaldırılamadı. Diğer pencereleri kapatıp tekrar dene."
fi

if [[ -d /usr/src/casper-wmi-1.0.0 ]]; then
    info "Eski DKMS kaydı temizleniyor..."
    sudo dkms remove casper-wmi/1.0.0 --all >/dev/null 2>&1 || true
    sudo rm -rf /usr/src/casper-wmi-1.0.0
fi

info "casper-wmi ${DRIVER_VER} kuruluyor..."
sudo mkdir -p "$SRC"
sudo cp "${SCRIPT_DIR}/driver/casper-wmi.c" "$SRC/"
sudo cp "${SCRIPT_DIR}/driver/Makefile"     "$SRC/"
sudo cp "${SCRIPT_DIR}/driver/dkms.conf"    "$SRC/"
sudo dkms add -m casper-wmi -v "$DRIVER_VER" 2>/dev/null || true
sudo dkms build -m casper-wmi -v "$DRIVER_VER" | tail -1
for kernel in /lib/modules/*/build; do
    [ -d "$kernel" ] || continue
    K="$(basename "$(dirname "$kernel")")"
    sudo dkms install -m casper-wmi -v "$DRIVER_VER" -k "$K" >/dev/null 2>&1 || true
done
sudo depmod -a
sudo modprobe casper_wmi
ok "casper-wmi yüklendi."

[[ -f /etc/modules-load.d/excalibur-center.conf ]] || \
    echo "casper_wmi" | sudo tee /etc/modules-load.d/excalibur-center.conf >/dev/null

LED_CONTROL="/sys/class/leds/casper::kbd_backlight/led_control"
[[ -e "$LED_CONTROL" ]] || fail "LED dosyası görünmedi: $LED_CONTROL"
ok "LED arayüzü hazır."

# ── 3. Uygulama dosyaları ────────────────────────────────────
APP_DIR="/opt/excalibur-center"
info "Uygulama kuruluyor: $APP_DIR"
sudo rm -rf "$APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo cp -r "${SCRIPT_DIR}/excalibur_center" "$APP_DIR/"

# ── 4. Sistem entegrasyonu ───────────────────────────────────
sudo install -Dm644 "${SCRIPT_DIR}/data/99-excalibur-center.rules" \
    /usr/lib/udev/rules.d/99-excalibur-center.rules
sudo install -Dm644 "${SCRIPT_DIR}/data/org.excalibur.center.policy" \
    /usr/share/polkit-1/actions/org.excalibur.center.policy
sudo install -Dm755 "${SCRIPT_DIR}/data/priv-write-helper" \
    /usr/lib/excalibur-center/priv-write-helper
sudo install -Dm644 "${SCRIPT_DIR}/data/excalibur-center.desktop" \
    /usr/share/applications/excalibur-center.desktop

# ── İkonlar ──────────────────────────────────────────────────
sudo install -Dm644 "${SCRIPT_DIR}/assets/excalibur-center.svg" \
    /usr/share/icons/hicolor/scalable/apps/excalibur-center.svg
for size in 512 256 128 64 48 32 16; do
    sudo install -Dm644 "${SCRIPT_DIR}/assets/icons/${size}/excalibur-center.png" \
        "/usr/share/icons/hicolor/${size}x${size}/apps/excalibur-center.png"
done
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true

sudo tee /usr/bin/excalibur-center >/dev/null <<'LAUNCHER'
#!/bin/bash
cd /opt/excalibur-center
exec /usr/bin/python3 -m excalibur_center.cli "$@"
LAUNCHER
sudo chmod 755 /usr/bin/excalibur-center

sudo install -Dm644 "${SCRIPT_DIR}/systemd/excalibur-center-restore.service" \
    /lib/systemd/system/excalibur-center-restore.service
sudo systemctl daemon-reload
sudo systemctl enable excalibur-center-restore.service >/dev/null

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo chgrp video "$LED_CONTROL" 2>/dev/null || true
sudo chmod 0660 "$LED_CONTROL" 2>/dev/null || true

getent group video >/dev/null && id -nG "$USER" | grep -qw video || {
    info "Kullanıcı video grubuna ekleniyor (yeniden giriş gerekebilir)..."
    sudo usermod -aG video "$USER"
}

ok "Kurulum tamamlandı!"
echo ""
echo "  Kullanım:"
echo "    excalibur-center            → GUI başlat"
echo "    excalibur-center --status   → mevcut durumu göster"
echo "    excalibur-center --help     → tüm komutlar"
echo ""
echo "  Uygulama menüsünde 'Excalibur Center' olarak da bulabilirsin."
echo ""
