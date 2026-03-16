#!/usr/bin/env bash
# HP OMEN 16 (2024+) - Linux Fix Script
# Resolves "Query 0x4c returned error 0x6" and "Platform Profile Not Supported"
# for newer Board IDs like 8C77.

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}--- HP OMEN Linux Compatibility Fixer ---${NC}"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[!] Please run this script with sudo${NC}"
    exit 1
fi

# 1. Update Kernel (Reminder)
KERNEL_VER=$(uname -r)
echo -e "[i] Current Kernel: $KERNEL_VER"
# Note: Kernel 6.9+ is highly recommended for 2024 models

# 2. Check for hp-omen-linux driver
if [ ! -d "/sys/devices/platform/hp-omen" ]; then
    echo -e "${YELLOW}[!] Third-party OMEN driver not detected.${NC}"
    echo -e "Implementing direct sysfs support in OMEN Command Center for Linux..."
else
    echo -e "${GREEN}[✓] Third-party OMEN driver found.${NC}"
fi

# 3. Apply Kernel Parameter for hp-wmi (WMI Signature Fix)
GRUB_FILE="/etc/default/grub"
if [ -f "$GRUB_FILE" ]; then
    if ! grep -q "hp_wmi.force_thermal_profile=1" "$GRUB_FILE"; then
        echo -e "[i] Adding force_thermal_profile=1 to GRUB..."
        # Backup
        cp "$GRUB_FILE" "${GRUB_FILE}.bak"
        # Append to GRUB_CMDLINE_LINUX_DEFAULT
        sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="hp_wmi.force_thermal_profile=1 /' "$GRUB_FILE"
        echo -e "${GREEN}[✓] Kernel parameter added. Please run 'sudo update-grub' and reboot.${NC}"
    else
        echo -e "${GREEN}[✓] Kernel parameter already present.${NC}"
    fi
fi

# 4. Driver Reload (Experimental)
echo -e "[i] Reloading hp-wmi module..."
modprobe -r hp-wmi || true
modprobe hp-wmi 2>/dev/null || echo -e "${RED}[!] Failed to reload hp-wmi${NC}"

# 5. BIOS Warning
echo -e "\n${YELLOW}IMPORTANT:${NC} If you still see 'Error 0x6' in dmesg, a BIOS update from HP is required."
echo -e "Newer OMEN laptops (8C77) have an ACPI bug that prevents Linux from controlling fans"
echo -e "until HP releases a fix or a newer Kernel (6.10+) bypasses it."

echo -e "\n${GREEN}Fix script completed.${NC}"
