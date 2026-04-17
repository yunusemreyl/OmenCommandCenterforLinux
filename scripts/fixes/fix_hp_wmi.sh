#!/usr/bin/env bash
# OMEN Command Center for Linux - WMI Fix / Restore Tool
# Restores the original stock hp-wmi kernel driver if you experience issues with
# the custom installed hp-wmi driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[0;31m[!] Please run this script with sudo\033[0m"
    exit 1
fi

echo -e "\033[1;33m--- Restoring Original HP-WMI Driver ---\033[0m"

# Uninstall custom DKMS module if it exists
if command -v dkms &>/dev/null; then
    # Try to grab version from dkms.conf, fallback if not found
    DKMS_VER=$(grep -oP 'PACKAGE_VERSION="\K[^"]+' "$REPO_ROOT/driver/dkms.conf" 2>/dev/null || echo "1.2.4")
    if dkms status "hp-rgb-lighting/$DKMS_VER" 2>/dev/null | grep -q "added"; then
        echo -e "[i] Removing custom hp-wmi from DKMS..."
        dkms remove -m "hp-rgb-lighting" -v "$DKMS_VER" --all 2>/dev/null || true
    fi
fi

# Look for backup files
KVER=$(uname -r)
FOUND_BACKUP=false
for BU_FILE in $(find \
    /lib/modules/"$KVER" \
    /usr/lib/modules/"$KVER" \
    -name "hp-wmi.ko*.backup" 2>/dev/null | sort -u); do
    ORIG_FILE="${BU_FILE%.backup}"
    echo -e "[i] Restoring $ORIG_FILE from backup..."
    mv "$BU_FILE" "$ORIG_FILE"
    FOUND_BACKUP=true
done

if [ "$FOUND_BACKUP" = false ]; then
    echo -e "\033[0;31m[!] No .backup driver found. Your stock driver might already be active or missing from module paths for $KVER.\033[0m"
else
    echo -e "[i] Module restored successfully. Running depmod..."
    depmod -a
fi

echo -e "[i] Reloading hp-wmi module..."
modprobe -r hp_wmi 2>/dev/null || true
modprobe hp_wmi 2>/dev/null || echo -e "\033[0;31m[!] Failed to reload hp-wmi. You might need to reboot.\033[0m"

echo -e "\033[0;32m[✓] Process complete. Your system should now be using the stock kernel fan driver.\033[0m"
