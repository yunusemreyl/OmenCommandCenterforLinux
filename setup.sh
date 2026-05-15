#!/usr/bin/env bash
# OMEN Command Center for Linux - Unified Setup Tool
# Handles installation, uninstallation, and updates.

set -euo pipefail

# --- CONFIGURATION ---
APP_NAME="OMEN Command Center for Linux"
INSTALL_DIR="/usr/libexec/hp-manager"
DATA_DIR="/usr/share/hp-manager"
BIN_LINK="/usr/bin/hp-manager"
CLI_LINK="/usr/bin/omen"
UNINSTALLER_LINK="/usr/bin/hp-manager-uninstall"
CONFIG_DIR="/etc/hp-manager"
VERSION="1.3.7"

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
# Check multiple locale variables; when running under sudo, try invoking user's locale
_detect_lang() {
    # Try the standard locale variables first
    for var in "${LC_MESSAGES:-}" "${LC_ALL:-}" "${LANG:-}" "${LANGUAGE:-}"; do
        if [ -n "$var" ]; then
            echo "${var:0:2}"
            return
        fi
    done
    # Under sudo, try the invoking user's locale
    if [ -n "${SUDO_USER:-}" ]; then
        local user_lang
        user_lang=$(su - "$SUDO_USER" -c 'echo "${LANG:-}"' 2>/dev/null || true)
        if [ -n "$user_lang" ]; then
            echo "${user_lang:0:2}"
            return
        fi
    fi
    echo "en"
}
LANG_CODE=$(_detect_lang)

# --- I18N MESSAGES ---
msg() {
    local key=$1
    shift || true
    if [ "$LANG_CODE" = "tr" ]; then
        case $key in
            "root_check")           printf '%s\n' "Bu scripti root olarak çalıştırın: sudo $0" ;;
            "pm_not_found")         printf '%s\n' "Desteklenen paket yöneticisi bulunamadı (pacman/apt/dnf/zypper)" ;;
            "pm_name")              printf '%s\n' "Paket yöneticisi: ${1:-}" ;;
            "installing_deps")      printf '%s\n' "Bağımlılıklar yükleniyor..." ;;
            "deps_installed")       printf '%s\n' "Bağımlılıklar yüklendi" ;;
            "installing_app")       printf '%s\n' "Uygulama kuruluyor..." ;;
            "daemon_installed")     printf '%s\n' "Daemon kuruldu: ${1:-}" ;;
            "gui_installed")        printf '%s\n' "GUI kuruldu: ${1:-}" ;;
            "images_copied")        printf '%s\n' "Resimler kopyalandı" ;;
            "success")              printf '%s\n' "${APP_NAME} başarıyla kuruldu!" ;;
            "uninstalling")         printf '%s\n' "Uygulama kaldırılıyor..." ;;
            "uninstalled")          printf '%s\n' "Uygulama kaldırıldı" ;;
            "updating")             printf '%s\n' "Uygulama güncelleniyor..." ;;
            "updated")              printf '%s\n' "Güncelleme tamamlandı!" ;;
            "usage")                printf '%s\n' "Kullanım: $0 [install|uninstall|update]" ;;
            "select_power_manager") printf '\n%s\n' "Hangi güç yöneticisini kullanmak istersiniz?" ;;
            "pm_detected")          printf '%b\n' "${CYAN}[i]${NC} Sistemde tespit edildi: ${1:-}" ;;
            "pm_already_present")   printf '%s\n' "Sistemde zaten bir güç yöneticisi var (${1:-}), kurulum atlanıyor." ;;
            "pm_opt_1")             printf '%s\n' "1) power-profiles-daemon (Varsayılan)" ;;
            "pm_opt_2")             printf '%s\n' "2) tuned-ppd (Fedora kullanıyorsanız önerilir)" ;;
            "pm_opt_3")             printf '%s\n' "3) TLP (https://github.com/linrunner/TLP)" ;;
            "pm_opt_4")             printf '%s\n' "4) auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)" ;;
            "pm_opt_5")             printf '%s\n' "5) Atla (Herhangi bir güç yöneticisi kurma)" ;;
            "pm_choice")            printf '%s' "Seçiminiz (1-5): " ;;
            "installing_pm")        printf '%s\n' "${1:-} kuruluyor..." ;;
            "pm_not_in_repo")       printf '%s\n' "Uyarı: ${1:-} paket yöneticinizde bulunamadı. Lütfen manuel kurun." ;;
            "skipping_pm")          printf '%s\n' "Güç yöneticisi kurulumu atlanıyor." ;;
            "driver_failed")        printf '%s\n' "Uyarı: Sürücü ${1:-} işlemi başarısız oldu. RGB kontrolü çalışmayabilir." ;;
            "driver_prompt")        printf '%s\n' "Özel hp-wmi/rgb DKMS sürücüsünü yüklemek istiyor musunuz?" ;;
            "driver_hint")          printf '%s\n' "Eğer kernel sürümünüz 7.0 veya üzerindeyseniz VE fan kontrolü zaten çalışıyorsa, bunu yüklemenize gerek YOKTUR." ;;
            "driver_choice")        printf '%s' "Özel sürücü yüklensin mi? (y/N): " ;;
            "driver_skipped")       printf '%s\n' "Özel sürücü kurulumu atlanıyor." ;;
            "rgb_driver_prompt")    printf '%s\n' "hp-rgb-lighting sürücüsünü yüklemek istiyor musunuz?" ;;
            "rgb_driver_note")      printf '%s\n' "  ⚠  Bu sürücü klavye RGB aydınlatma kontrolü için ZORUNLUDUR." ;;
            "rgb_driver_choice")    printf '%s' "hp-rgb-lighting yüklensin mi? (y/N): " ;;
            "rgb_driver_skipped")   printf '%s\n' "hp-rgb-lighting kurulumu atlanıyor. Klavye RGB aydınlatma kontrolü kullanılamayacak." ;;
            "wmi_driver_prompt")    printf '%s\n' "Yamalı hp-wmi sürücüsünü yüklemek istiyor musunuz?" ;;
            "wmi_driver_note")      printf '%s\n' "  Kernel sürümünüz 7.0 altında — fan/ısıl kontrol için bu sürücü gereklidir." ;;
            "wmi_driver_choice")    printf '%s' "Yamalı hp-wmi yüklensin mi? (y/N): " ;;
            "wmi_driver_skipped")   printf '%s\n' "Yamalı hp-wmi kurulumu atlanıyor." ;;
            "help_title")           printf '%s\n' "Komutlar:" ;;
            "help_install")         printf '%s\n' "  install    - Uygulama ve kernel sürücüsünün tam kurulumu" ;;
            "help_uninstall")       printf '%s\n' "  uninstall  - Uygulama ve sürücünün tamamen kaldırılması (ayarlar korunur)" ;;
            "help_update")          printf '%s\n' "  update     - Son değişiklikleri çek ve yeniden kur" ;;
            "help_example")         printf '%s\n' "Örnek: sudo $0 install" ;;
            *)                      printf '%s\n' "$key" ;;
        esac
    else
        case $key in
            "root_check")           printf '%s\n' "Run this script as root: sudo $0" ;;
            "pm_not_found")         printf '%s\n' "Supported package manager not found (pacman/apt/dnf/zypper)" ;;
            "pm_name")              printf '%s\n' "Package manager: ${1:-}" ;;
            "installing_deps")      printf '%s\n' "Installing dependencies..." ;;
            "deps_installed")       printf '%s\n' "Dependencies installed" ;;
            "installing_app")       printf '%s\n' "Installing application..." ;;
            "daemon_installed")     printf '%s\n' "Daemon installed: ${1:-}" ;;
            "gui_installed")        printf '%s\n' "GUI installed: ${1:-}" ;;
            "images_copied")        printf '%s\n' "Images copied" ;;
            "success")              printf '%s\n' "${APP_NAME} successfully installed!" ;;
            "uninstalling")         printf '%s\n' "Uninstalling application..." ;;
            "uninstalled")          printf '%s\n' "Application uninstalled" ;;
            "updating")             printf '%s\n' "Updating application..." ;;
            "updated")              printf '%s\n' "Update complete!" ;;
            "usage")                printf '%s\n' "Usage: $0 [install|uninstall|update]" ;;
            "select_power_manager") printf '\n%s\n' "Which power manager would you like to use?" ;;
            "pm_detected")          printf '%b\n' "${CYAN}[i]${NC} Detected on system: ${1:-}" ;;
            "pm_already_present")   printf '%s\n' "A power manager is already present (${1:-}), skipping installation." ;;
            "pm_opt_1")             printf '%s\n' "1) power-profiles-daemon (Default)" ;;
            "pm_opt_2")             printf '%s\n' "2) tuned-ppd (Recommended for Fedora users)" ;;
            "pm_opt_3")             printf '%s\n' "3) TLP (https://github.com/linrunner/TLP)" ;;
            "pm_opt_4")             printf '%s\n' "4) auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)" ;;
            "pm_opt_5")             printf '%s\n' "5) Skip (Don't install any power manager)" ;;
            "pm_choice")            printf '%s' "Your choice (1-5): " ;;
            "installing_pm")        printf '%s\n' "Installing ${1:-}..." ;;
            "pm_not_in_repo")       printf '%s\n' "Warning: ${1:-} was not found in your package manager. Please install it manually." ;;
            "skipping_pm")          printf '%s\n' "Skipping power manager installation." ;;
            "driver_failed")        printf '%s\n' "Warning: Driver ${1:-} failed. RGB control may not work." ;;
            "driver_prompt")        printf '%s\n' "Do you want to install the custom hp-wmi/rgb driver via DKMS?" ;;
            "driver_hint")          printf '%s\n' "If your kernel is 7.0 or higher AND you can control fans out-of-the-box, you do NOT need this." ;;
            "driver_choice")        printf '%s' "Install custom driver? (y/N): " ;;
            "driver_skipped")       printf '%s\n' "Skipping custom driver installation." ;;
            "rgb_driver_prompt")    printf '%s\n' "Do you want to install the hp-rgb-lighting driver?" ;;
            "rgb_driver_note")      printf '%s\n' "  ⚠  This driver is REQUIRED for keyboard RGB lighting control." ;;
            "rgb_driver_choice")    printf '%s' "Install hp-rgb-lighting? (y/N): " ;;
            "rgb_driver_skipped")   printf '%s\n' "Skipping hp-rgb-lighting installation. Keyboard RGB lighting control will not be available." ;;
            "wmi_driver_prompt")    printf '%s\n' "Do you want to install the patched hp-wmi driver?" ;;
            "wmi_driver_note")      printf '%s\n' "  Your kernel is below 7.0 — this driver is needed for fan/thermal control." ;;
            "wmi_driver_choice")    printf '%s' "Install patched hp-wmi? (y/N): " ;;
            "wmi_driver_skipped")   printf '%s\n' "Skipping patched hp-wmi installation." ;;
            "help_title")           printf '%s\n' "Commands:" ;;
            "help_install")         printf '%s\n' "  install    - Full installation of application and kernel driver" ;;
            "help_uninstall")       printf '%s\n' "  uninstall  - Complete removal of application and driver (keeps config)" ;;
            "help_update")          printf '%s\n' "  update     - Pull latest changes and reinstall" ;;
            "help_example")         printf '%s\n' "Example: sudo $0 install" ;;
            *)                      printf '%s\n' "$key" ;;
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

    # dnf check must come before pacman — Fedora/Nobara may have both
    if [ -f /etc/fedora-release ] || [ -f /etc/nobara-release ] || command -v dnf &>/dev/null; then
        PM="dnf"
        INSTALL_CMD="dnf install -y"
    elif command -v pacman &>/dev/null; then
        PM="pacman"
        INSTALL_CMD="pacman -S --noconfirm --needed"
    elif command -v apt &>/dev/null; then
        PM="apt"
        INSTALL_CMD="env DEBIAN_FRONTEND=noninteractive apt install -y"
    elif command -v zypper &>/dev/null; then
        PM="zypper"
        INSTALL_CMD="zypper install -y"
    else
        err "$(msg pm_not_found)"
    fi
    log "$(msg pm_name "$PM")"
}

# --- POWER MANAGER DETECTION ---
# Returns the name of the first active power manager found, or empty string.
detect_active_power_manager() {
    # Check running services first (most reliable)
    local services=(
        "power-profiles-daemon"
        "tuned"
        "tuned-ppd"
        "tlp"
        "auto-cpufreq"
    )
    for svc in "${services[@]}"; do
        if systemctl is-active --quiet "${svc}.service" 2>/dev/null; then
            echo "$svc"
            return
        fi
    done

    # Check installed binaries as fallback
    command -v tlp        &>/dev/null && { echo "tlp";        return; }
    command -v auto-cpufreq &>/dev/null && { echo "auto-cpufreq"; return; }

    # Check installed packages as last resort
    if command -v rpm &>/dev/null; then
        for pkg in power-profiles-daemon tuned tuned-ppd tlp; do
            rpm -q "$pkg" &>/dev/null 2>&1 && { echo "$pkg"; return; }
        done
    fi
    if command -v dpkg &>/dev/null; then
        for pkg in power-profiles-daemon tlp auto-cpufreq; do
            dpkg -l "$pkg" 2>/dev/null | grep -q "^ii" && { echo "$pkg"; return; }
        done
    fi
    if command -v pacman &>/dev/null; then
        for pkg in power-profiles-daemon tlp auto-cpufreq; do
            pacman -Q "$pkg" &>/dev/null 2>&1 && { echo "$pkg"; return; }
        done
    fi

    echo ""
}

# --- INSTALL DEPENDENCIES ---
install_dependencies() {
    info "$(msg installing_deps)"

    # Base packages — power manager NOT included here
    case $PM in
        pacman)
            $INSTALL_CMD python python-gobject gtk4 libadwaita python-pydbus python-cairo
            ;;
        apt)
            $INSTALL_CMD python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 python3-pydbus python3-cairo
            ;;
        dnf|zypper)
            $INSTALL_CMD python3 python3-gobject gtk4 libadwaita python3-pydbus python3-cairo
            ;;
    esac

    # --- Power Manager ---
    # If one is already active/installed, skip entirely — no question asked.
    local existing_pm
    existing_pm=$(detect_active_power_manager)

    if [ -n "$existing_pm" ]; then
        log "$(msg pm_already_present "$existing_pm")"
    else
        # Nothing found — ask the user which one to install
        msg select_power_manager
        msg pm_opt_1
        msg pm_opt_2
        msg pm_opt_3
        msg pm_opt_4
        msg pm_opt_5
        msg pm_choice
        read -r choice

        case ${choice:-1} in
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
                # Default (1 or Enter): power-profiles-daemon
                local pkg="power-profiles-daemon"
                info "$(msg installing_pm "$pkg")"
                if ! $INSTALL_CMD "$pkg" 2>/dev/null; then
                    warn "$(msg pm_not_in_repo "$pkg")"
                fi
                ;;
        esac
    fi

    log "$(msg deps_installed)"
}

# --- DRIVER MANAGEMENT ---
manage_driver() {
    local action=$1
    if [ -d "driver" ] && [ -f "driver/setup.sh" ]; then
        if [ "$action" = "install" ]; then
            # Detect kernel version and board to decide which prompts to show
            local kver_major kver_minor board_name
            kver_major=$(uname -r | cut -d. -f1)
            kver_minor=$(uname -r | cut -d. -f2)
            board_name=$(cat /sys/devices/virtual/dmi/id/board_name 2>/dev/null | tr '[:lower:]' '[:upper:]' || echo "")

            # stock hp-wmi (kernel 7.0+) already handles fan/thermal control
            local stock_fan_support=true
            if [ "$kver_major" -lt 7 ]; then
                stock_fan_support=false
            fi
            case "$board_name" in
                8D41) stock_fan_support=false ;; # OMEN Max 16 still needs patched hp-wmi
            esac

            # ── Prompt 1: hp-rgb-lighting (always shown — required for keyboard RGB) ──
            printf '\n%s\n' "--------------------------------------------------------"
            msg rgb_driver_prompt
            msg rgb_driver_note
            printf '%s\n' "--------------------------------------------------------"
            msg rgb_driver_choice
            read -r rgb_choice

            local install_rgb=false
            if [[ "$rgb_choice" =~ ^[Yy]$ ]]; then
                install_rgb=true
            else
                warn "$(msg rgb_driver_skipped)"
            fi

            # ── Prompt 2: patched hp-wmi (only when kernel < 7.0 or special board) ──
            local install_wmi=false
            if ! $stock_fan_support; then
                printf '\n%s\n' "--------------------------------------------------------"
                msg wmi_driver_prompt
                msg wmi_driver_note
                printf '%s\n' "--------------------------------------------------------"
                msg wmi_driver_choice
                read -r wmi_choice

                if [[ "$wmi_choice" =~ ^[Yy]$ ]]; then
                    install_wmi=true
                else
                    info "$(msg wmi_driver_skipped)"
                fi
            fi

            # Nothing selected — skip driver installation entirely
            if ! $install_rgb && ! $install_wmi; then
                return
            fi

            # When only RGB was requested (kernel < 7.0 case), force rgb-only mode
            if $install_rgb && ! $install_wmi; then
                export FORCE_RGB_ONLY=true
            fi
        fi
        info "Running driver ${action}..."
        if ! (cd driver && chmod +x setup.sh && ./setup.sh "$action"); then
            warn "$(msg driver_failed "$action")"
            if [ "$action" = "install" ]; then
                warn "Continuing installation — RGB control will be unavailable until driver is fixed."
            fi
        else
            if [ "$action" = "install" ]; then
                info "Applying kernel module configuration..."

                # Unload stock hp_wmi before loading our DKMS override.
                info "Unloading stock hp_wmi module..."
                modprobe -r hp_wmi 2>/dev/null || true

                info "Loading modules via modprobe..."
                if modprobe hp-wmi 2>/dev/null; then
                    log "hp-wmi loaded successfully"
                else
                    warn "hp-wmi failed to load — check: dmesg | tail -20"
                fi

                if modprobe hp-rgb-lighting 2>/dev/null; then
                    log "hp-rgb-lighting loaded successfully"
                else
                    warn "hp-rgb-lighting failed to load"
                fi

                info "Active module path (debug):"
                modinfo hp_wmi 2>/dev/null | grep filename || warn "hp_wmi not found by modinfo"
            fi
        fi
    else
        warn "Driver directory or setup script not found — skipping driver ${action}."
    fi
}

# --- OMEN KEY SHORTCUT BINDING ---
# Binds the OMEN key (KEY_PROG2 / XF86Launch2) to launch hp-manager
# for the invoking user's desktop environment.
setup_omen_key_shortcut() {
    local real_user="${SUDO_USER:-}"
    if [ -z "$real_user" ]; then
        warn "Cannot detect invoking user — skipping Omen key shortcut setup."
        return
    fi

    local real_home
    real_home=$(eval echo "~${real_user}")

    # Detect DE from the invoking user's session
    local de=""
    de=$(su - "$real_user" -c 'echo "${XDG_CURRENT_DESKTOP:-}"' 2>/dev/null || true)
    de=$(echo "$de" | tr '[:upper:]' '[:lower:]')

    info "Setting up Omen Key shortcut (DE: ${de:-unknown}, user: $real_user)"

    case "$de" in
        *gnome*|*budgie*|*unity*)
            _setup_omen_key_gnome "$real_user"
            ;;
        *kde*|*plasma*)
            _setup_omen_key_kde "$real_user" "$real_home"
            ;;
        *xfce*)
            _setup_omen_key_xfce "$real_user"
            ;;
        *cinnamon*)
            _setup_omen_key_cinnamon "$real_user"
            ;;
        *)
            _setup_omen_key_fallback "$real_user" "$real_home"
            ;;
    esac
}

_setup_omen_key_gnome() {
    local user=$1
    local base_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
    local omen_path="${base_path}/omen-key/"

    # Read existing custom keybindings, append ours if not already present
    local existing
    existing=$(su - "$user" -c "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings" 2>/dev/null || echo "[]")

    if echo "$existing" | grep -q "omen-key"; then
        info "Omen Key shortcut already configured in GNOME"
        return
    fi

    # Append our keybinding path
    if [ "$existing" = "@as []" ] || [ "$existing" = "[]" ]; then
        local new_val="['${omen_path}']"
    else
        local new_val
        new_val=$(echo "$existing" | sed "s/]$/, '${omen_path}']/" )
    fi

    su - "$user" -c "
        gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \"${new_val}\"
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${omen_path} name 'OMEN Command Center'
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${omen_path} command 'hp-manager'
        gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:${omen_path} binding 'Launch2'
    " 2>/dev/null && log "Omen Key shortcut set for GNOME (Launch2 → hp-manager)" \
                   || warn "Failed to set GNOME shortcut — you can set it manually in Settings → Keyboard → Shortcuts"
}

_setup_omen_key_kde() {
    local user=$1
    local home=$2
    local rc_file="${home}/.config/kglobalshortcutsrc"

    # Ensure config dir exists
    su - "$user" -c "mkdir -p '${home}/.config'" 2>/dev/null || true

    # Check if already configured
    if [ -f "$rc_file" ] && grep -q "omen-command-center" "$rc_file" 2>/dev/null; then
        info "Omen Key shortcut already configured in KDE"
        return
    fi

    # Try kwriteconfig6 first (Plasma 6), then kwriteconfig5
    local kwrite=""
    if command -v kwriteconfig6 &>/dev/null; then
        kwrite="kwriteconfig6"
    elif command -v kwriteconfig5 &>/dev/null; then
        kwrite="kwriteconfig5"
    fi

    if [ -n "$kwrite" ]; then
        su - "$user" -c "
            ${kwrite} --file kglobalshortcutsrc --group 'omen-command-center.desktop' --key '_launch' 'Launch2,none,OMEN Command Center'
            ${kwrite} --file kglobalshortcutsrc --group 'omen-command-center.desktop' --key '_k_friendly_name' 'OMEN Command Center'
            if command -v qdbus6 &>/dev/null; then
                qdbus6 org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reloadConfig || true
            elif command -v qdbus &>/dev/null; then
                qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reloadConfig || true
            fi
        " 2>/dev/null && log "Omen Key shortcut set for KDE Plasma (Launch2 → hp-manager)" \
                       || warn "Failed to set KDE shortcut — set it in System Settings → Shortcuts"
    else
        # Direct file write as fallback
        cat >> "$rc_file" <<'KDE_SHORTCUT'

[omen-command-center.desktop]
_launch=Launch2,none,OMEN Command Center
_k_friendly_name=OMEN Command Center
KDE_SHORTCUT
        chown "$user":"$user" "$rc_file" 2>/dev/null || true
        log "Omen Key shortcut written to kglobalshortcutsrc"
    fi

    # Create the .desktop file for KDE service menu
    local desktop_dir="${home}/.local/share/applications"
    su - "$user" -c "mkdir -p '${desktop_dir}'" 2>/dev/null || true
    cat > "${desktop_dir}/omen-command-center.desktop" <<DESKTOP
[Desktop Entry]
Name=OMEN Command Center
Exec=hp-manager
Icon=omenapplogo
Type=Application
Categories=System;Settings;
DESKTOP
    chown "$user":"$user" "${desktop_dir}/omen-command-center.desktop" 2>/dev/null || true
}

_setup_omen_key_xfce() {
    local user=$1

    su - "$user" -c "
        xfconf-query -c xfce4-keyboard-shortcuts -p '/commands/custom/XF86Launch2' -n -t string -s 'hp-manager'
    " 2>/dev/null && log "Omen Key shortcut set for XFCE (XF86Launch2 → hp-manager)" \
                   || warn "Failed to set XFCE shortcut — set it in Settings → Keyboard → Application Shortcuts"
}

_setup_omen_key_cinnamon() {
    local user=$1
    local base_path="/org/cinnamon/desktop/keybindings/custom-keybindings"
    local omen_path="${base_path}/omen-key/"

    su - "$user" -c "
        dconf write ${omen_path}name \"'OMEN Command Center'\"
        dconf write ${omen_path}command \"'hp-manager'\"
        dconf write ${omen_path}binding \"['Launch2']\"
    " 2>/dev/null && log "Omen Key shortcut set for Cinnamon (Launch2 → hp-manager)" \
                   || warn "Failed to set Cinnamon shortcut — set it in Keyboard → Shortcuts"
}

_setup_omen_key_fallback() {
    local user=$1
    local home=$2
    local xbindkeys_conf="${home}/.xbindkeysrc"

    # Check if xbindkeys is available
    if ! command -v xbindkeys &>/dev/null; then
        info "Omen Key: Unknown DE and xbindkeys not installed."
        info "To bind the OMEN key manually, map XF86Launch2 to 'hp-manager' in your DE's shortcut settings."
        return
    fi

    # Check if already configured
    if [ -f "$xbindkeys_conf" ] && grep -q "hp-manager" "$xbindkeys_conf" 2>/dev/null; then
        info "Omen Key shortcut already configured in xbindkeys"
        return
    fi

    # Append binding
    cat >> "$xbindkeys_conf" <<'XBIND'

# OMEN Command Center key (auto-generated)
"hp-manager"
    XF86Launch2
XBIND
    chown "$user":"$user" "$xbindkeys_conf" 2>/dev/null || true
    log "Omen Key shortcut added to ~/.xbindkeysrc (XF86Launch2 → hp-manager)"
    info "Run 'xbindkeys' to activate, or add it to your session autostart."
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

    # CLI files
    cp src/omen-cli.py "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/omen-cli.py"

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

    # CLI link
    ln -sf "$INSTALL_DIR/omen-cli.py" "$CLI_LINK"

    # System integration
    mkdir -p /etc/dbus-1/system.d
    mkdir -p /usr/share/polkit-1/actions
    mkdir -p /usr/share/applications

    # Ensure legacy monolithic service is stopped and removed
    systemctl stop com.yyl.hpmanager.service 2>/dev/null || true
    systemctl disable com.yyl.hpmanager.service 2>/dev/null || true
    rm -f /etc/systemd/system/com.yyl.hpmanager.service
    rm -f /etc/dbus-1/system.d/com.yyl.hpmanager.conf

    for svc in fan rgb power mux platform; do
        if [ -f "data/com.yyl.hpmanager.${svc}.conf" ]; then
            cp "data/com.yyl.hpmanager.${svc}.conf" /etc/dbus-1/system.d/
        fi
        if [ -f "data/hpm-${svc}.service" ]; then
            cp "data/hpm-${svc}.service" /etc/systemd/system/
        fi
    done
    cp data/com.yyl.hpmanager.desktop /usr/share/applications/

    # Ensure drivers load on boot via modules-load.d
    echo "hp-rgb-lighting" > /etc/modules-load.d/hp-rgb-lighting.conf
    echo "hp-wmi"          > /etc/modules-load.d/hp-wmi.conf

    # Uninstaller — self-contained, does not rely on original script path
    cat > "$UNINSTALLER_LINK" << 'UNINSTALLER'
#!/usr/bin/env bash
# OMEN Command Center for Linux — Uninstaller (auto-generated)
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root: sudo hp-manager-uninstall"
    exit 1
fi

INSTALL_DIR="/usr/libexec/hp-manager"
DATA_DIR="/usr/share/hp-manager"
BIN_LINK="/usr/bin/hp-manager"
CLI_LINK="/usr/bin/omen"
UNINSTALLER_LINK="/usr/bin/hp-manager-uninstall"

echo "Stopping and disabling services..."
systemctl stop    hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
systemctl disable hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
for svc in fan rgb power mux platform; do
    systemctl stop "hpm-${svc}.service" 2>/dev/null || true
    systemctl disable "hpm-${svc}.service" 2>/dev/null || true
done

echo "Removing files..."
rm -f /etc/systemd/system/hp-manager.service
rm -f /etc/systemd/system/com.yyl.hpmanager.service
rm -f "$BIN_LINK"
rm -f "$CLI_LINK"
rm -rf "$INSTALL_DIR"
rm -rf "$DATA_DIR"
rm -rf "/var/lib/hp-manager"
rm -f /etc/dbus-1/system.d/com.yyl.hpmanager.conf
for svc in fan rgb power mux platform; do
    rm -f "/etc/systemd/system/hpm-${svc}.service"
    rm -f "/etc/dbus-1/system.d/com.yyl.hpmanager.${svc}.conf"
done
rm -f /usr/share/applications/com.yyl.hpmanager.desktop
rm -f /usr/share/icons/hicolor/48x48/apps/omenapplogo.png
rm -f /etc/modules-load.d/hp-rgb-lighting.conf
rm -f /etc/modules-load.d/hp-wmi.conf

systemctl daemon-reload
echo "[✓] OMEN Command Center for Linux uninstalled."

# Remove this uninstaller last
rm -f "$UNINSTALLER_LINK"
UNINSTALLER
    chmod +x "$UNINSTALLER_LINK"

    systemctl daemon-reload
    for svc in fan rgb power mux platform; do
        systemctl enable "hpm-${svc}.service" || true
        systemctl restart "hpm-${svc}.service" || warn "Daemon hpm-${svc} failed to start"
    done

    # Omen Key shortcut
    setup_omen_key_shortcut

    log "$(msg success)"
}

# --- UNINSTALL APP ---
do_uninstall() {
    check_root
    info "$(msg uninstalling)"

    systemctl stop    hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
    systemctl disable hp-manager.service com.yyl.hpmanager.service 2>/dev/null || true
    for svc in fan rgb power mux platform; do
        systemctl stop "hpm-${svc}.service" 2>/dev/null || true
        systemctl disable "hpm-${svc}.service" 2>/dev/null || true
    done

    manage_driver "uninstall"

    rm -f /etc/systemd/system/hp-manager.service
    rm -f /etc/systemd/system/com.yyl.hpmanager.service
    rm -f "$BIN_LINK"
    rm -f "$CLI_LINK"
    rm -f "$UNINSTALLER_LINK"
    rm -rf "$INSTALL_DIR"
    rm -rf "$DATA_DIR"
    rm -rf "/var/lib/hp-manager"
    rm -f /etc/dbus-1/system.d/com.yyl.hpmanager.conf
    for svc in fan rgb power mux platform; do
        rm -f "/etc/systemd/system/hpm-${svc}.service"
        rm -f "/etc/dbus-1/system.d/com.yyl.hpmanager.${svc}.conf"
    done
    rm -f /usr/share/applications/com.yyl.hpmanager.desktop
    rm -f /usr/share/icons/hicolor/48x48/apps/omenapplogo.png
    rm -f /etc/modules-load.d/hp-rgb-lighting.conf
    rm -f /etc/modules-load.d/hp-wmi.conf

    systemctl daemon-reload
    log "$(msg uninstalled)"
}

# --- UPDATE APP ---
do_update() {
    check_root
    info "$(msg updating)"

    if [ -d ".git" ]; then
        info "Pulling latest changes..."
        git stash 2>/dev/null || true
        git pull
        # Re-exec with the freshly updated script so bash reads the new version
        info "Restarting setup with updated script..."
        exec "$0" _update_apply
    fi

    do_uninstall
    do_install

    log "$(msg updated)"
}

# --- MAIN ---
if [ $# -eq 0 ]; then
    echo -e "${CYAN}${APP_NAME} - Unified Setup Tool (v${VERSION})${NC}"
    echo "$(msg usage)"
    echo ""
    msg help_title
    msg help_install
    msg help_uninstall
    msg help_update
    echo ""
    msg help_example
    exit 0
fi

case "${1}" in
    install)        do_install ;;
    uninstall)      do_uninstall ;;
    update)         do_update ;;
    _update_apply)  do_uninstall; do_install; log "$(msg updated)" ;;
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
