#!/usr/bin/env bash
# HP Laptop Manager - Unified Setup Tool
# Handles installation, uninstallation, and updates.

set -euo pipefail

# --- CONFIGURATION ---
APP_NAME="HP Laptop Manager"
INSTALL_DIR="/usr/libexec/hp-manager"
DATA_DIR="/usr/share/hp-manager"
BIN_LINK="/usr/bin/hp-manager"
UNINSTALLER_LINK="/usr/bin/hp-manager-uninstall"
CONFIG_DIR="/etc/hp-manager"
VERSION="1.1.4"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging helpers
log()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
info()  { echo -e "${CYAN}[i]${NC} $*"; }
debug() { echo -e "${BLUE}[DEBUG]${NC} $*"; }

# Language detection — sudo root ortamında LANG boş gelebilir, fallback "en"
LANG_CODE=${LANG:-en}
LANG_CODE=${LANG_CODE:0:2}

# --- I18N MESSAGES ---
msg() {
    local key=$1
    shift || true
    if [ "$LANG_CODE" = "tr" ]; then
        case $key in
            "root_check")         printf '%s\n' "Bu scripti root olarak çalıştırın: sudo $0" ;;
            "pm_not_found")       printf '%s\n' "Desteklenen paket yöneticisi bulunamadı (pacman/apt/dnf/zypper)" ;;
            "pm_name")            printf '%s\n' "Paket yöneticisi: ${1:-}" ;;
            "installing_deps")    printf '%s\n' "Bağımlılıklar yükleniyor..." ;;
            "deps_installed")     printf '%s\n' "Bağımlılıklar yüklendi" ;;
            "installing_app")     printf '%s\n' "Uygulama kuruluyor..." ;;
            "daemon_installed")   printf '%s\n' "Daemon kuruldu: ${1:-}" ;;
            "gui_installed")      printf '%s\n' "GUI kuruldu: ${1:-}" ;;
            "images_copied")      printf '%s\n' "Resimler kopyalandı" ;;
            "success")            printf '%s\n' "${APP_NAME} başarıyla kuruldu!" ;;
            "uninstalling")       printf '%s\n' "Uygulama kaldırılıyor..." ;;
            "uninstalled")        printf '%s\n' "Uygulama kaldırıldı" ;;
            "updating")           printf '%s\n' "Uygulama güncelleniyor..." ;;
            "updated")            printf '%s\n' "Güncelleme tamamlandı!" ;;
            "usage")              printf '%s\n' "Kullanım: $0 [install|uninstall|update]" ;;
            "select_power_manager") printf '\n%s\n' "Hangi güç yöneticisini kullanmak istersiniz?" ;;
            "pm_detected")        printf '%b\n' "${CYAN}[i]${NC} Sistemde tespit edildi: ${1:-}" ;;
            "pm_opt_1")           printf '%s\n' "1) power-profiles-daemon (Varsayılan)" ;;
            "pm_opt_2")           printf '%s\n' "2) tuned-ppd (Fedora kullanıyorsanız önerilir)" ;;
            "pm_opt_3")           printf '%s\n' "3) TLP (https://github.com/linrunner/TLP)" ;;
            "pm_opt_4")           printf '%s\n' "4) auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)" ;;
            "pm_opt_5")           printf '%s\n' "5) Atla (Herhangi bir güç yöneticisi kurma)" ;;
            "pm_choice")          printf '%s' "Seçiminiz (1-5): " ;;
            "installing_pm")      printf '%s\n' "${1:-} kuruluyor..." ;;
            "pm_not_in_repo")     printf '%s\n' "Uyarı: ${1:-} paket yöneticinizde bulunamadı. Lütfen manuel kurun." ;;
            "skipping_pm")        printf '%s\n' "Güç yöneticisi kurulumu atlanıyor." ;;
            "driver_failed")      printf '%s\n' "Uyarı: Sürücü ${1:-} işlemi başarısız oldu. RGB kontrolü çalışmayabilir." ;;
            *)                    printf '%s\n' "$key" ;;
        esac
    else
        case $key in
            "root_check")         printf '%s\n' "Run this script as root: sudo $0" ;;
            "pm_not_found")       printf '%s\n' "Supported package manager not found (pacman/apt/dnf/zypper)" ;;
            "pm_name")            printf '%s\n' "Package manager: ${1:-}" ;;
            "installing_deps")    printf '%s\n' "Installing dependencies..." ;;
            "deps_installed")     printf '%s\n' "Dependencies installed" ;;
            "installing_app")     printf '%s\n' "Installing application..." ;;
            "daemon_installed")   printf '%s\n' "Daemon installed: ${1:-}" ;;
            "gui_installed")      printf '%s\n' "GUI installed: ${1:-}" ;;
            "images_copied")      printf '%s\n' "Images copied" ;;
            "success")            printf '%s\n' "${APP_NAME} successfully installed!" ;;
            "uninstalling")       printf '%s\n' "Uninstalling application..." ;;
            "uninstalled")        printf '%s\n' "Application uninstalled" ;;
            "updating")           printf '%s\n' "Updating application..." ;;
            "updated")            printf '%s\n' "Update complete!" ;;
            "usage")              printf '%s\n' "Usage: $0 [install|uninstall|update]" ;;
            "select_power_manager") printf '\n%s\n' "Which power manager would you like to use?" ;;
            "pm_detected")        printf '%b\n' "${CYAN}[i]${NC} Detected on system: ${1:-}" ;;
            "pm_opt_1")           printf '%s\n' "1) power-profiles-daemon (Default)" ;;
            "pm_opt_2")           printf '%s\n' "2) tuned-ppd (Recommended for Fedora users)" ;;
            "pm_opt_3")           printf '%s\n' "3) TLP (https://github.com/linrunner/TLP)" ;;
            "pm_opt_4")           printf '%s\n' "4) auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)" ;;
            "pm_opt_5")           printf '%s\n' "5) Skip (Don't install any power manager)" ;;
            "pm_choice")          printf '%s' "Your choice (1-5): " ;;
            "installing_pm")      printf '%s\n' "Installing ${1:-}..." ;;
            "pm_not_in_repo")     printf '%s\n' "Warning: ${1:-} was not found in your package manager. Please install it manually." ;;
            "skipping_pm")        printf '%s\n' "Skipping power manager installation." ;;
            "driver_failed")      printf '%s\n' "Warning: Driver ${1:-} failed. RGB control may not work." ;;
            *)                    printf '%s\n' "$key" ;;
        esac
    fi
}

# --- ROOT CHECK ---
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "$(msg root_check)"
    fi
}

# --- DISTRO DETECTION ---
detect_pm() {
    if [ -f /etc/os-release ]; then
        _DISTRO_NAME=$(. /etc/os-release && echo "${PRETTY_NAME:-${NAME:-unknown}}")
        info "Detected distro: $_DISTRO_NAME"
    fi

    if [ -f /etc/fedora-release ] || [ -f /etc/nobara-release ] || command -v dnf &>/dev/null; then
        PM="dnf"
        INSTALL_CMD="dnf install -y"
    elif command -v pacman &>/dev/null; then
        PM="pacman"
        INSTALL_CMD="pacman -S --noconfirm --needed"
    elif command -v apt &>/dev/null; then
        PM="apt"
        INSTALL_CMD="apt install -y"
    elif command -v zypper &>/dev/null; then
        PM="zypper"
        INSTALL_CMD="zypper install -y"
    else
        err "$(msg pm_not_found)"
    fi
    log "$(msg pm_name "$PM")"
}

# --- INSTALL DEPENDENCIES ---
install_dependencies() {
    info "$(msg installing_deps)"

    case $PM in
        pacman)
            $INSTALL_CMD python python-gobject gtk4 libadwaita python-pydbus python-cairo
            ;;
        apt)
            $INSTALL_CMD python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-pydbus python3-cairo
            ;;
        dnf|zypper)
            $INSTALL_CMD python3 python3-gobject gtk4 libadwaita python3-pydbus python3-cairo
            ;;
    esac

    # Power Manager Detection
    local detected=()
    if systemctl list-unit-files power-profiles-daemon.service 2>/dev/null | grep -q "power-profiles-daemon"; then
        detected+=("power-profiles-daemon")
    fi
    command -v tlp &>/dev/null          && detected+=("TLP")
    command -v auto-cpufreq &>/dev/null && detected+=("auto-cpufreq")
    if command -v tuned &>/dev/null || { command -v rpm &>/dev/null && rpm -q tuned &>/dev/null 2>/dev/null; }; then
        detected+=("tuned")
    fi

    # Power Manager Selection
    msg select_power_manager
    if [ ${#detected[@]} -gt 0 ]; then
        msg pm_detected "${detected[*]}"
    fi

    msg pm_opt_1
    msg pm_opt_2
    msg pm_opt_3
    msg pm_opt_4
    msg pm_opt_5
    # pm_choice uses printf '%s' (no newline) so read appears on same line
    msg pm_choice
    read -r choice

    case $choice in
        2)
            local pkg="tuned-ppd"
            info "$(msg installing_pm "$pkg")"
            $INSTALL_CMD "$pkg" || warn "$(msg pm_not_in_repo "$pkg")"
            ;;
        3)
            local pkg="tlp"
            info "$(msg installing_pm "$pkg")"
            $INSTALL_CMD "$pkg" || warn "$(msg pm_not_in_repo "$pkg")"
            ;;
        4)
            local pkg="auto-cpufreq"
            info "$(msg installing_pm "$pkg")"
            $INSTALL_CMD "$pkg" || warn "$(msg pm_not_in_repo "$pkg")"
            ;;
        5)
            info "$(msg skipping_pm)"
            ;;
        *)
            local pkg="power-profiles-daemon"
            info "$(msg installing_pm "$pkg")"
            $INSTALL_CMD "$pkg" || warn "$(msg pm_not_in_repo "$pkg")"
            ;;
    esac

    log "$(msg deps_installed)"
}

# --- DRIVER MANAGEMENT ---
manage_driver() {
    local action=$1
    if [ -d "driver" ] && [ -f "driver/setup.sh" ]; then
        info "Running driver ${action}..."
        if ! (cd driver && chmod +x setup.sh && ./setup.sh "$action"); then
            warn "$(msg driver_failed "$action")"
            # Not fatal for uninstall; fatal for install since RGB won't work
            if [ "$action" = "install" ]; then
                warn "Continuing installation — RGB control will be unavailable until driver is fixed."
            fi
        fi
    else
        warn "Driver directory or setup script not found — skipping driver ${action}."
    fi
}

# --- INSTALL APP ---
do_install() {
    check_root
    detect_pm
    install_dependencies

    info "$(msg installing_app)"

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DATA_DIR/images"
    mkdir -p "$CONFIG_DIR"

    # Driver
    manage_driver "install"

    # Daemon files
    cp -r src/daemon/* "$INSTALL_DIR/"

    # GUI files
    mkdir -p "$DATA_DIR/gui/pages"
    mkdir -p "$DATA_DIR/gui/widgets"
    cp src/gui/main_window.py "$DATA_DIR/gui/"
    cp src/gui/i18n.py        "$DATA_DIR/gui/"
    cp src/gui/pages/*.py     "$DATA_DIR/gui/pages/"
    cp src/gui/widgets/*.py   "$DATA_DIR/gui/widgets/"

    # Images (non-fatal if missing)
    if [ -d "images" ] && [ -n "$(ls -A images 2>/dev/null)" ]; then
        cp images/* "$DATA_DIR/images/"
        log "$(msg images_copied)"
    else
        warn "No images directory found — skipping image copy."
    fi

    # Launcher script
    cat > "$BIN_LINK" << 'LAUNCHER'
#!/bin/bash
cd /usr/share/hp-manager/gui
exec python3 /usr/share/hp-manager/gui/main_window.py "$@"
LAUNCHER
    chmod +x "$BIN_LINK"

    # System integration
    mkdir -p /etc/dbus-1/system.d
    mkdir -p /usr/share/polkit-1/actions
    mkdir -p /usr/share/applications

    cp data/com.yyl.hpmanager.conf    /etc/dbus-1/system.d/
    cp data/com.yyl.hpmanager.service /etc/systemd/system/com.yyl.hpmanager.service
    cp data/com.yyl.hpmanager.policy  /usr/share/polkit-1/actions/
    cp data/com.yyl.hpmanager.desktop /usr/share/applications/

    # Ensure RGB driver loads on boot
    echo "hp-rgb-lighting" > /etc/modules-load.d/hp-rgb-lighting.conf

    # Uninstaller — self-contained, does not rely on original script path
    cat > "$UNINSTALLER_LINK" << 'UNINSTALLER'
#!/usr/bin/env bash
# HP Laptop Manager — Uninstaller (auto-generated)
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo hp-manager-uninstall"
    exit 1
fi

INSTALL_DIR="/usr/libexec/hp-manager"
DATA_DIR="/usr/share/hp-manager"
BIN_LINK="/usr/bin/hp-manager"
UNINSTALLER_LINK="/usr/bin/hp-manager-uninstall"

echo "Stopping and disabling services..."
systemctl stop    hp-manager.service com.yyl.hpmanager.service hp-omen-key.service 2>/dev/null || true
systemctl disable hp-manager.service com.yyl.hpmanager.service hp-omen-key.service 2>/dev/null || true

echo "Removing files..."
rm -f /etc/systemd/system/hp-manager.service
rm -f /etc/systemd/system/com.yyl.hpmanager.service
rm -f /etc/systemd/system/hp-omen-key.service
rm -f "$BIN_LINK"
rm -rf "$INSTALL_DIR"
rm -rf "$DATA_DIR"
rm -f /etc/dbus-1/system.d/com.yyl.hpmanager.conf
rm -f /usr/share/polkit-1/actions/com.yyl.hpmanager.policy
rm -f /usr/share/applications/com.yyl.hpmanager.desktop
rm -f /usr/share/icons/hicolor/48x48/apps/hp_logo.png
rm -f /etc/udev/rules.d/90-hp-omen-key.rules
rm -f /etc/modules-load.d/hp-rgb-lighting.conf

systemctl daemon-reload
echo "[✓] HP Laptop Manager uninstalled."

# Remove this uninstaller last
rm -f "$UNINSTALLER_LINK"
UNINSTALLER
    chmod +x "$UNINSTALLER_LINK"

    systemctl daemon-reload
    systemctl enable  com.yyl.hpmanager.service
    systemctl restart com.yyl.hpmanager.service || warn "Daemon failed to start — check: journalctl -u com.yyl.hpmanager.service"

    log "$(msg success)"
}

# --- UNINSTALL APP ---
do_uninstall() {
    check_root
    info "$(msg uninstalling)"

    systemctl stop    hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
    systemctl disable hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
    systemctl stop    hp-omen-key.service 2>/dev/null || true
    systemctl disable hp-omen-key.service 2>/dev/null || true

    manage_driver "uninstall"

    rm -f /etc/systemd/system/hp-manager.service
    rm -f /etc/systemd/system/com.yyl.hpmanager.service
    rm -f /etc/systemd/system/hp-omen-key.service
    rm -f "$BIN_LINK"
    rm -f "$UNINSTALLER_LINK"
    rm -rf "$INSTALL_DIR"
    rm -rf "$DATA_DIR"
    rm -f /etc/dbus-1/system.d/com.yyl.hpmanager.conf
    rm -f /usr/share/polkit-1/actions/com.yyl.hpmanager.policy
    rm -f /usr/share/applications/com.yyl.hpmanager.desktop
    rm -f /usr/share/icons/hicolor/48x48/apps/hp_logo.png
    rm -f /etc/udev/rules.d/90-hp-omen-key.rules
    rm -f /etc/modules-load.d/hp-rgb-lighting.conf

    systemctl daemon-reload
    log "$(msg uninstalled)"
}

# --- UPDATE APP ---
do_update() {
    check_root   # FIX: was missing
    info "$(msg updating)"

    if [ -d ".git" ]; then
        info "Pulling latest changes..."
        git stash 2>/dev/null || true
        git pull
    fi

    do_uninstall
    do_install

    log "$(msg updated)"
}

# --- MAIN ---
if [ $# -eq 0 ]; then
    echo -e "${CYAN}${APP_NAME} - Unified Setup Tool (v${VERSION})${NC}"
    echo "Usage: sudo $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    - Full installation of application and kernel driver"
    echo "  uninstall  - Complete removal of application and driver (keeps config)"
    echo "  update     - Pull latest changes and reinstall"
    echo ""
    echo "Example: sudo $0 install"
    exit 0
fi

case "${1}" in
    install)   do_install ;;
    uninstall) do_uninstall ;;
    update)    do_update ;;
    -h|--help)
        msg usage
        echo "Options: install, uninstall, update"
        exit 0
        ;;
    *)
        msg usage
        exit 1
        ;;
esac
