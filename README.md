
 # OMEN Command Center for Linux v1.3.6 #
<p align="center">
  <img src="images/omenapplogo.png" alt="Logo" width="250">

## 📖 About The Project
<p align="center">
  <img src="screenshots/start.png" alt="Launcher" width="45%">
  <img src="screenshots/dash.png" alt="Dashboard" width="45%">
</p>
<p align="center">
  <img src="screenshots/keyboard.png" alt="Keyboard" width="45%">
  <img src="screenshots/mux.png" alt="MUX Switch" width="45%">
</p>
<p align="center">
  <img src="screenshots/settings.png" alt="Settings" width="45%">
  <img src="screenshots/performance.png" alt="Performance" width="45%">
</p>

**OMEN Command Center for Linux** is a native Linux application designed to unlock the full potential of HP Omen and Victus series laptops. It serves as an open-source alternative to the official OMEN Gaming Hub, providing essential controls in a modern, user-friendly interface.

---

## 🛠️ What's New in v1.3.6?

### 🔧 Critical Bug Fixes
- **Fixed GUI not launching** after upgrading from v1.3.0 to v1.3.5. The service architecture transition left stale references that prevented the interface from starting.
- **Fixed Fan Page temperature/power profile display**: The fan page's background monitor was calling `GetSystemInfo()` and `GetPowerProfile()` on the wrong service, resulting in 0°C readings and non-functional power profile buttons.
- **Fixed language switch disconnection**: Switching language destroyed all pages but never reconnected daemon services, leaving the app fully offline until restart.
- **Improved debug diagnostics**: The debug console now checks all 5 microservices (`hpm-fan`, `hpm-rgb`, `hpm-power`, `hpm-mux`, `hpm-platform`) instead of only one.

### 🧩 Architecture (since v1.3.5)
The system runs **5 independent microservices**, each dedicated to a specific task:

| Service | Responsibility |
|---------|---------------|
| `hpm-fan` | Fan control, curve management, mode switching |
| `hpm-rgb` | RGB keyboard lighting, effects engine |
| `hpm-power` | Power profiles (eco / balanced / performance) |
| `hpm-mux` | GPU mode switching (envycontrol, supergfxctl, prime-select) |
| `hpm-platform` | System temperatures, battery info, keyboard fixes |

This architecture ensures that if one service (e.g., RGB) fails, critical functions like fan control or GPU switching continue uninterrupted.

### ⚡ Performance Highlights (since v1.3.5)
- **RGB Engine**: Static color mode enters deep sleep using `Event.wait()`, consuming 0% CPU.
- **Smart GPU Monitoring**: Checks Nvidia GPU power state before polling — won't force-wake the dGPU, extending battery life.
- **Dynamic Backoff**: Polling intervals expand when system values remain unchanged.

### 🎮 GPU TGP 80W Cap Mitigation (HP Omen Max 16)
The chronic issue in mainline kernels (v7.0+) that capped GPU power at 80W on certain Omen models (board `8D41`) has been fixed. Thanks to a patch by **xcellsior**, unnecessary firmware writes at probe time are now gated.

---

## ✨ Features

### 🎨 RGB Lighting Control
- **4-Zone Control**: Customize colors for different keyboard zones.
- **Effects**: Static, Breathing, Wave, Cycle.
- **Brightness & Speed**: Adjustable parameters for dynamic effects.
- **Low-CPU Wave Engine**: Wave mode CPU usage dropped from ~22-28% to ~2% in stress conditions.

### 📊 System Dashboard
- **Real-time Monitoring**: CPU/GPU temperatures, fan speeds, battery health.
- **Performance Profiles**: One-click power profile switching (requires `power-profiles-daemon`).

### 🌪️ Fan Control
- **Standard Mode**: EC-controlled automatic fan management.
- **Max Mode**: Forces fans to maximum speed for intensive tasks.
- **Custom Mode**: Drag-and-drop curve editor to create your own fan profiles.

### 🎮 GPU MUX Switch (BETA)
- Switch between **Hybrid**, **Discrete**, and **Integrated** modes.
- Backend can be selected from **Settings → GPU / MUX**.
- Auto mode prefers `envycontrol` / `supergfxctl` / `prime-select` before HP WMI direct.
- ⚠️ Some hardware/BIOS combinations may require a reboot.

### ⌨️ Desktop Shortcuts (Recommended)
 To minimize background resource usage, we recommend creating a **Custom Shortcut** in your Desktop Environment settings (GNOME, KDE, etc.):
 - **Command**: `hp-manager`
 - **Shortcut Key**: Your **OMEN Key** (detected as `KEY_PROG2`) or any preferred key combination.

---

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
Note: For compatibility with older documentation, `sudo ./install.sh` redirects to `setup.sh install`.
Installation Warning ⚠️: We recommend restarting your computer after installation.

### Updating

```bash
cd OmenCommandCenterforLinux
git pull
sudo ./setup.sh update
```

> ⚠️ **Upgrading from v1.3.0 or earlier?** The architecture changed from a single monolithic daemon to microservices. You **must** use `sudo ./setup.sh update` to cleanly remove old services and install the new ones.

### Script Layout

Maintenance scripts are organized under:

- `scripts/fixes/`
- `scripts/diagnostics/`
- `scripts/tests/`

Legacy entry points (`fix_hp_wmi.sh`, `fix_omen.sh`, `dump_log.sh`, `test_nvidia.py`) are kept at the repository root as compatibility wrappers.

For OMEN Max 16 / hp-wmi probe troubleshooting, use:
- `scripts/tests/test_hp_wmi_raw_payload.sh`

The installer will automatically:
1. Detect your package manager and install dependencies.
2. Detect your kernel version and install the appropriate driver:
   - **Kernel ≥ 7.0**: Only installs `hp-rgb-lighting` (RGB). Fan control is provided by the stock `hp-wmi` module.
     - **Exception**: OMEN Max 16 board `8D41` is forced to the custom `hp-wmi` path due to stock probe incompatibility.
   - **Kernel < 7.0**: Installs both the custom `hp-wmi` driver (backported) and `hp-rgb-lighting`.
3. Install the daemon and GUI components.
4. Set up the 5 microservices.

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
- **Kernel Module Development**: Special thanks to **[TUXOV](https://github.com/TUXOV/hp-wmi-fan-and-backlight-control)** for the `hp-wmi-fan-and-backlight-control` driver. Also thanks to **xcellsior** for the Nvidia Dynamic Boost 80W cap mitigation patch.

## ⚖️ Legal Disclaimer
This tool is an independent open-source project developed by **yunusemreyl**.
It is **NOT** affiliated with or endorsed by **Hewlett-Packard (HP)**.
The software is provided "as is", without warranty of any kind.

---
*Developed with ❤️ by yunusemreyl*
