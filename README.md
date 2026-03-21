
 # OMEN Command Center for Linux v1.2.1 #
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

**New in v1.2.1:**

- 🛠 **Kernel Driver**: Fixed `-22` (EINVAL) probe crash on **8D41** (OMEN MAX 16-ah0xxx). Fixed MUX switch `Invalid Argument` on **8C77** by correcting WMI write buffer size.
- ⌨️ **Touchpad Fix**: Resolved conflicts with touchpad toggle keys (F11/F12). Redundant events are now handled at the kernel level.
- ⚠️ **MUX Beta**: MUX Switch functionality is in **BETA**. We recommend `envycontrol` or `prime-select` for the most stable experience while we work on further fixes.
- 📦 **DKMS & Installer**: Resolved `Module already installed` errors during kernel updates and fixed AUR `PKGBUILD` issues.
- ⚡ **Performance**: Removed background OMEN Key listener thread to reduce idle CPU usage.


## ✨ Features

### 🎨 RGB Lighting Control
- **4-Zone Control**: Customize colors for different keyboard zones.
- **Effects**: Static, Breathing, Wave, Cycle.
- **Brightness & Speed**: Adjustable parameters for dynamic effects.

### 📊 System Dashboard
- **Real-time Monitoring**: CPU/GPU temperatures and Fan speeds.
- **Performance Profiles**: One-click power profile switching (requires `power-profiles-daemon`).

### 🌪️ Fan Control
- **Standard Mode**: Intelligent software-controlled fan curve for balanced noise/performance.
- **Max Mode**: Forces fans to maximum speed for intensive tasks.
- **Custom Mode**: Drag-and-drop curve editor to create your own fan profiles.

### 🎮 GPU MUX Switch (BETA)
- Switch between **Hybrid**, **Discrete**, and **Integrated** modes.
- ⚠️ **Warning**: MUX Switch functionality is currently in **Beta**. We are actively working to resolve remaining "Invalid Argument" (Errno 22) errors on some hardware versions.
- **Recommendation**: For the most stable GPU switching experience, we currently recommend using dedicated tools like [`envycontrol`](https://github.com/bayasandaa/envycontrol) or `prime-select`.

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
