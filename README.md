
 # OMEN Command Center for Linux v1.2.3 #
<p align="center">
  <img src="images/omenapplogo.png" alt="Logo" width="250">

## 📖 About The Project
<p align="center">
  <img src="screenshots/dashboard.png" alt="Dashboard" width="45%">
  <img src="screenshots/performance.png" alt="Fan Control" width="45%">
</p>
<p align="center">
  <img src="screenshots/lighting.png" alt="Lighting" width="45%">
  <img src="screenshots/keys.png" alt="MUX Switch" width="45%">
</p>
<p align="center">
  <img src="screenshots/settings.png" alt="Settings" width="45%">
</p>

**OMEN Command Center for Linux** is a native Linux application designed to unlock the full potential of HP Omen and Victus series laptops. It serves as an open-source alternative to the official OMEN Gaming Hub, providing essential controls in a modern, user-friendly interface.

**Hi everyone, I had to take a break from development due to my midterm week. I'll be back with more development work and exciting new things starting Thursday, April 16th.**

**New in v1.2.3:**

- 🌪️ **Fan/Platform Compatibility**: Improved board handling for OMEN MAX / 8D87-class devices by aligning Victus-S parameter paths with confirmed working behavior.
- 🛠 **Installer Reliability**: DKMS install flow improved to reduce repeat-install conflicts and avoid early stock driver backup before successful build/install.
- 🧰 **Recovery Improvements**: Restore tooling now checks both `/lib/modules` and `/usr/lib/modules`, improving Arch/CachyOS recovery paths.
- 🎮 **MUX Backend Stability**: Backend selection is now configurable from Settings, with auto-priority favoring external tools (`envycontrol`, `supergfxctl`, `prime-select`) before HP WMI direct mode.
- 🔐 **Privileged MUX Commands**: MUX apply actions use interactive authentication prompts for privileged backend commands.
- 🧪 **Errno 22 Mitigation**: HP WMI `graphics_mode` writes now try multiple payload formats to reduce model-specific `Invalid Argument (22)` failures.
- 🌈 **Wave Effect Optimization**: Wave now shifts smoothly across your selected keyboard colors (instead of HSV rainbow), and applies thresholded zone writes for significantly lower CPU usage under animation load.


## ✨ Features

### 🎨 RGB Lighting Control
- **4-Zone Control**: Customize colors for different keyboard zones.
- **Effects**: Static, Breathing, Wave, Cycle.
- **Brightness & Speed**: Adjustable parameters for dynamic effects.
- **Low-CPU Wave Engine**: On tested systems, wave mode CPU usage dropped from ~22-28% average to ~2% average in stress conditions.

### 📊 System Dashboard
- **Real-time Monitoring**: CPU/GPU temperatures and Fan speeds.
- **Performance Profiles**: One-click power profile switching (requires `power-profiles-daemon`).

### 🌪️ Fan Control
- **Standard Mode**: Intelligent software-controlled fan curve for balanced noise/performance.
- **Max Mode**: Forces fans to maximum speed for intensive tasks.
- **Custom Mode**: Drag-and-drop curve editor to create your own fan profiles.

### 🎮 GPU MUX Switch (BETA)
- Switch between **Hybrid**, **Discrete**, and **Integrated** modes.
- Backend can be selected from **Settings → GPU / MUX**.
- Auto mode now prefers `envycontrol` / `supergfxctl` / `prime-select` before HP WMI direct.
- ⚠️ Some hardware/BIOS combinations may still require reboot or vendor-specific tooling behavior.

### ⌨️ Desktop Shortcuts (Recommended)
 To minimize background resource usage, we have removed the active OMEN Key listener daemon. We highly recommend creating a **Custom Shortcut** in your Desktop Environment settings (GNOME, KDE, etc.):
 - **Command**: `hp-manager`
 - **Shortcut Key**: Your **OMEN Key** (detected as `KEY_PROG2`) or any preferred key combinations.
 This provides a much more responsive experience compared to a background listener thread.

## 🚀 Installation

### Prerequisites
- A Linux distribution (Ubuntu, Fedora, Arch, OpenSUSE, etc.)
- `git` installed

### Install
Open a terminal and run:

```bash
# Clone the repository
git clone https://github.com/yunusemreyl/OmenCommandCenterforLinux.git
cd OmenCommandCenterforLinux

# Run the installer (requires root)
chmod +x setup.sh
sudo ./setup.sh install
```
Installation Warning⚠️: We recommend restart your computer after installation.

### Script Layout

Maintenance scripts are now organized under:

- `scripts/fixes/`
- `scripts/diagnostics/`
- `scripts/tests/`

Legacy entry points (`fix_hp_wmi.sh`, `fix_omen.sh`, `dump_log.sh`, `test_nvidia.py`) are kept at the repository root as compatibility wrappers.

The installer will automatically:
1. Detect your package manager and install dependencies.
2. Detect your kernel version and install the appropriate driver:
   - **Kernel ≥ 7.0**: Only installs `hp-rgb-lighting` (RGB). Fan control is provided by the stock `hp-wmi` module.
   - **Kernel < 7.0**: Installs both the custom `hp-wmi` driver (backported) and `hp-rgb-lighting`.
3. Install the daemon and GUI components.
4. Set up system services.
5. Provide a troubleshooting guide if issues occur.

## 🗑️ Uninstallation

To completely remove the application and its services:

```bash
cd OmenCommandCenterforLinux
sudo ./setup.sh uninstall
```

## 🐧 Compatibility

| Distribution | Status | Notes |
|--------------|--------|-------|
| **Ubuntu 24.04 LTS / Zorin OS / Pop!_OS / Linux Mint** | ✅ Verified | Full support via `apt` |
| **Fedora 42+ / Nobara** | ✅ Verified | Full support via `dnf` |
| **Arch Linux / CachyOS / Manjaro** | ✅ Verified | Full support via `pacman` |
| **OpenSUSE Tumbleweed** | ✅ Verified | Full support via `zypper` |


## 👨‍💻 Credits & Acknowledgments
- **Lead Developer**: [yunusemreyl](https://github.com/yunusemreyl)
- **Contributors**: [ja4e](https://github.com/ja4e), [babyinlinux](https://github.com/babyinlinux), [entharia](https://github.com/entharia) 
- **Kernel Module Development**: Special thanks to **[TUXOV](https://github.com/TUXOV/hp-wmi-fan-and-backlight-control)** for the `hp-wmi-fan-and-backlight-control` driver, which makes fan control possible.

## ⚖️ Legal Disclaimer
This tool is an independent open-source project developed by **yunusemreyl**.
It is **NOT** affiliated with or endorsed by **Hewlett-Packard (HP)**.
The software is provided “as is”, without warranty of any kind.

---
*Developed with ❤️ by yunusemreyl*
