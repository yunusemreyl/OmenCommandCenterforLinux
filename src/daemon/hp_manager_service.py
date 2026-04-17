#!/usr/bin/env python3
"""OMEN Command Center for Linux - D-Bus Daemon Service
Runs as root to provide hardware access.
"""
import sys, os, time, threading, logging, json, copy, colorsys, math, shutil, subprocess, re, typing, glob, platform
from gi.repository import GLib
from pydbus import SystemBus

# --- PATHS ---
DRIVER_PATH_CUSTOM = "/sys/devices/platform/hp-rgb-lighting"
CONFIG_FILE = "/etc/hp-manager/state.json"

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hp-manager")

lock = threading.RLock()
_cache_lock = threading.Lock()
state_changed = threading.Event()
_system_sleeping = threading.Event()  # Flag to pause operations during sleep/wake
HEX_COLOR_RE = re.compile(r"^[0-9A-F]{6}$")
VALID_LIGHT_MODES = {"static", "breathing", "cycle", "wave"}
VALID_DIRECTIONS = {"ltr", "rtl"}
VALID_GPU_MODES = {"hybrid", "discrete", "integrated"}


# ============================================================
# FAN CONTROLLER
# ============================================================
class FanController:
    def __init__(self):
        self.hwmon_path = self._find_hwmon()
        self.fan_count = 0
        self.found_fans = []
        self.max_speeds = {}
        self.mode = "auto"
        if self.hwmon_path:
            self._detect_fans()
            self._read_max_speeds()
            self._read_current_mode()

    def _find_hwmon(self):
        for path in glob.glob("/sys/class/hwmon/hwmon*/name"):
            try:
                with open(path, 'r') as f:
                    name = f.read().strip()
                    if name in ("hp", "hp-omen"):
                        logger.info(f"Found HP/OMEN hwmon at {os.path.dirname(path)} (driver={name})")
                        return os.path.dirname(path)
            except Exception:
                pass

        for platform_name in ("hp-wmi", "hp_wmi", "hp-omen"):
            platform_hwmon = f"/sys/devices/platform/{platform_name}/hwmon"
            if os.path.exists(platform_hwmon):
                try:
                    entries = sorted(os.listdir(platform_hwmon))
                    if entries:
                        path = os.path.join(platform_hwmon, entries[0])
                        logger.info(f"Found HP hwmon via platform device at {path}")
                        return path
                except Exception:
                    pass

        logger.warning("No HP hwmon device found")
        return None

    def _detect_fans(self):
        if not self.hwmon_path:
            return
        for f in os.listdir(self.hwmon_path):
            if f.startswith("fan") and f.endswith("_input"):
                try:
                    self.found_fans.append(int(f[3:-6]))
                except ValueError:
                    continue
        self.found_fans.sort()
        self.fan_count = len(self.found_fans)

    def _read_max_speeds(self):
        if not self.hwmon_path:
            return
        for i in self.found_fans:
            max_path = os.path.join(self.hwmon_path, f"fan{i}_max")
            try:
                with open(max_path) as f:
                    self.max_speeds[i] = int(f.read().strip())
            except Exception:
                self.max_speeds[i] = 6000

    def _read_current_mode(self):
        if not self.hwmon_path:
            return
        pwm_path = os.path.join(self.hwmon_path, "pwm1_enable")
        try:
            with open(pwm_path) as f:
                val = int(f.read().strip())
            self.mode = {0: "max", 1: "custom"}.get(val, "auto")
        except Exception:
            self.mode = "auto"

    def _sysfs_read(self, filename):
        if not self.hwmon_path:
            return 0
        try:
            with open(os.path.join(self.hwmon_path, filename)) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def _sysfs_write(self, filename, value):
        if not self.hwmon_path:
            return False
        try:
            with open(os.path.join(self.hwmon_path, filename), "w") as f:
                f.write(str(value))
            return True
        except Exception as e:
            logger.error(f"sysfs write {filename}={value} error: {e}")
            return False

    def get_fan_count(self):
        return self.fan_count

    def get_max_speed(self, fan_num):
        return self.max_speeds.get(fan_num, 6000)

    def get_current_speed(self, fan_num):
        speed = self._sysfs_read(f"fan{fan_num}_input")
        if speed == 0:
            speed = self._try_fan_speed_fallback(fan_num)
        return speed

    def _try_fan_speed_fallback(self, fan_num):
        """Try alternative hwmon paths when the primary one returns 0 RPM."""
        # Search other hwmon devices for fan speed data
        for path in glob.glob("/sys/class/hwmon/hwmon*/fan*_input"):
            try:
                basename = os.path.basename(path)
                hwmon_dir = os.path.dirname(path)
                # Skip our own hwmon (already tried)
                if hwmon_dir == self.hwmon_path:
                    continue
                # Match fan number
                idx = basename.replace("fan", "").replace("_input", "")
                if idx == str(fan_num):
                    with open(path) as f:
                        val = int(f.read().strip())
                    if val > 0:
                        return val
            except Exception:
                continue
        return 0

    def get_target_speed(self, fan_num):
        return self._sysfs_read(f"fan{fan_num}_target")

    def set_mode(self, mode):
        if not self.hwmon_path:
            return False
        val = {"auto": 2, "max": 0, "custom": 1}.get(mode)
        if val is None:
            return False

        # Avoid re-writing the same mode: some EC/firmware combos may
        # briefly reset fan behavior when mode is written redundantly.
        if self.get_mode() == mode:
            logger.info(f"Fan mode already {mode}, skipping write")
            return True

        ok = self._sysfs_write("pwm1_enable", val)

        if not ok and mode == "max":
            # Fallback path for firmware where pwm1_enable alone does not
            # apply max cooling.
            for profile_path, profile_value in (
                ("/sys/devices/platform/hp-wmi/thermal_profile", "1"),
                ("/sys/devices/platform/hp-omen/thermal_profile", "1"),
                ("/sys/firmware/acpi/platform_profile", "performance"),
                ("/sys/devices/platform/hp-wmi/platform_profile", "performance"),
            ):
                if not os.path.exists(profile_path):
                    continue
                try:
                    with open(profile_path, "w") as f:
                        f.write(profile_value)
                    ok = True
                    break
                except Exception:
                    pass

        if ok:
            self.mode = mode
            logger.info(f"Fan mode set to {mode}")
        return ok

    def set_fan_target(self, fan_num, rpm):
        if not self.hwmon_path or fan_num not in self.found_fans:
            return False
        rpm = max(0, min(rpm, self.get_max_speed(fan_num)))
        ok = self._sysfs_write(f"fan{fan_num}_target", rpm)
        if ok:
            logger.info(f"Fan {fan_num} target set to {rpm} RPM")
        return ok

    def is_available(self):
        return self.hwmon_path is not None and self.fan_count > 0

    def get_mode(self):
        if self.hwmon_path:
            self._read_current_mode()
        return self.mode


# ============================================================
# RGB CONTROLLER
# ============================================================
class RGBController:
    def __init__(self):
        self.driver_path = self._find_rgb_path()
        self.available = self.driver_path is not None
        self.last_written = [None] * 8
        self.reversed = True
        self._fds = {}
        if self.available:
            for i in range(8):
                try:
                    self._fds[i] = open(f"{self.driver_path}/zone{i}", "w")
                except Exception:
                    pass

    def _find_rgb_path(self):
        if os.path.exists(DRIVER_PATH_CUSTOM):
            logger.info(f"RGB: Using custom driver path {DRIVER_PATH_CUSTOM}")
            return DRIVER_PATH_CUSTOM

        try:
            with open("/proc/modules") as f:
                loaded = f.read()
            if "hp_rgb_lighting" in loaded:
                for candidate in ("/sys/devices/platform/hp-rgb-lighting",
                                  "/sys/devices/platform/hp_rgb_lighting"):
                    if os.path.exists(candidate):
                        logger.info(f"RGB: Found loaded module at {candidate}")
                        return candidate
        except Exception:
            pass

        logger.info("RGB: No RGB control path found (hp-rgb-lighting not loaded)")
        return None

    def is_available(self):
        return self.available

    def write_zone(self, zone, hex_color):
        if not self.available or not (0 <= zone <= 7):
            return

        target_zone = zone
        if self.reversed and 0 <= zone <= 3:
            target_zone = 3 - zone

        if self.last_written[target_zone] == hex_color:
            return

        try:
            time.sleep(0.001)
            fd = self._fds.get(target_zone)
            if fd:
                fd.seek(0)
                fd.write(hex_color)
                fd.flush()
            else:
                with open(f"{self.driver_path}/zone{target_zone}", "w") as f:
                    f.write(hex_color)
            self.last_written[target_zone] = hex_color
        except Exception:
            try:
                with open(f"{self.driver_path}/zone{target_zone}", "w") as f:
                    f.write(hex_color)
                self.last_written[target_zone] = hex_color
                self._fds[target_zone] = open(f"{self.driver_path}/zone{target_zone}", "w")
            except Exception:
                pass

    def write_all(self, hex_list):
        for i, hc in enumerate(hex_list[:8]):
            self.write_zone(i, hc)

    def write_brightness(self, on):
        if not self.available:
            return
        try:
            with open(f"{self.driver_path}/brightness", "w") as f:
                f.write("1" if on else "0")
                f.flush()
        except Exception:
            pass

    def write_win_lock(self, locked):
        if not self.available:
            return
        try:
            with open(f"{self.driver_path}/win_lock", "w") as f:
                f.write("1" if locked else "0")
                f.flush()
        except Exception:
            pass


# ============================================================
# POWER PROFILE CONTROLLER
# ============================================================
class PowerProfileController:
    PPD_BUS    = "net.hadess.PowerProfiles"
    PPD_PATH   = "/net/hadess/PowerProfiles"
    TUNED_BUS  = "com.redhat.tuned"
    TUNED_PATH = "/Tuned"

    def __init__(self):
        self.mode = "ppd"
        self.available = False
        self.bus = SystemBus()
        self.proxy = None

        try:
            self.proxy = self.bus.get(self.TUNED_BUS, self.TUNED_PATH)
            self.proxy.active_profile()
            self.mode = "tuned"
            self.available = True
            logger.info("PowerProfileController: Using Tuned backend")
        except Exception:
            try:
                self.proxy = self.bus.get(self.PPD_BUS, self.PPD_PATH)
                self.mode = "ppd"
                self.available = True
                logger.info("PowerProfileController: Using Power-Profiles-Daemon backend")
            except Exception:
                if os.path.exists("/sys/devices/platform/hp-wmi/thermal_profile") or \
                   os.path.exists("/sys/devices/platform/hp-omen/thermal_profile"):
                    self.mode = "omen_direct"
                    self.available = True
                    logger.info("PowerProfileController: Using OMEN Direct sysfs backend")
                else:
                    self.proxy = None
                    self.available = False
                    logger.warning("PowerProfileController: No power profile backend found")

    def get_profiles(self):
        if not self.available:
            return []
        if self.mode == "ppd":
            try:
                return [p["Profile"] for p in self.proxy.Profiles]
            except Exception:
                return ["power-saver", "balanced", "performance"]
        return ["power-saver", "balanced", "performance"]

    def get_active(self):
        if not self.available:
            return "balanced"
        try:
            if self.mode == "ppd":
                return self.proxy.ActiveProfile
            if self.mode == "tuned":
                tp = self.proxy.active_profile()
                if "powersave" in tp:   return "power-saver"
                if "performance" in tp: return "performance"
                return "balanced"
            return state.get("power_profile", "balanced")
        except Exception:
            return "balanced"

    def set_profile(self, profile):
        if not self.available:
            return False
        try:
            if self.mode == "ppd":
                self.proxy.ActiveProfile = profile
            elif self.mode == "tuned":
                mapping = {
                    "power-saver": "powersave",
                    "balanced":    "balanced",
                    "performance": "throughput-performance",
                }
                self.proxy.switch_profile(mapping.get(profile, "balanced"))
            elif self.mode == "omen_direct":
                val = {"power-saver": "0", "balanced": "0", "performance": "1"}.get(profile, "0")
                for path in ("/sys/devices/platform/hp-wmi/thermal_profile",
                             "/sys/devices/platform/hp-omen/thermal_profile"):
                    if os.path.exists(path):
                        with open(path, "w") as f:
                            f.write(val)
                        break

            threading.Thread(target=self._sync_nvidia_power, args=(profile,), daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"Power profile set error ({self.mode}): {e}")
            return False

    def _sync_nvidia_power(self, profile):
        try:
            if not shutil.which("nvidia-smi"):
                return

            if profile == "performance":
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=power.max_limit", "--format=csv,noheader,nounits"],
                    timeout=2.0
                ).decode().strip()
                if out:
                    limit = int(float(out))
                    subprocess.run(["nvidia-smi", "-pl", str(limit)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                    logger.info(f"NVIDIA GPU locked to MAX Performance: {limit}W")
            else:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=power.default_limit", "--format=csv,noheader,nounits"],
                    timeout=2.0
                ).decode().strip()
                if out:
                    limit = int(float(out))
                    subprocess.run(["nvidia-smi", "-pl", str(limit)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                    logger.info(f"NVIDIA GPU restored to DEFAULT Base: {limit}W")
        except Exception as e:
            logger.warning(f"Failed to sync NVIDIA power curve: {e}")


# ============================================================
# MUX CONTROLLER
# ============================================================

_BIOS_MUX_PATH = "/sys/devices/platform/hp-wmi/graphics_mode"

_BIOS_MUX_READ  = {0: "integrated", 1: "discrete", 2: "hybrid"}
_BIOS_MUX_WRITE = {"integrated": 0, "discrete": 1, "hybrid": 2}


class MUXController:
    def __init__(self):
        self.envycontrol  = shutil.which("envycontrol")
        self.supergfxctl  = shutil.which("supergfxctl")
        self.prime_select = shutil.which("prime-select")
        self.backend: typing.Optional[str] = None
        self._cached_mode = "unknown"
        self._last_check = 0.0
        self._detect_backend()

    def _detect_backend(self):
        # FIX: read forced backend from state safely (state may not exist yet at init)
        try:
            with lock:
                forced = state.get("mux_backend", "auto")
        except Exception:
            forced = "auto"

        available = self.get_available_backends()

        if forced != "auto" and forced in available:
            self.backend = forced
            logger.info(f"MUX backend: {self.backend} (forced by user)")
            return

        # Auto-detect priority: envycontrol > supergfxctl > prime-select > bios
        if "envycontrol" in available:
            self.backend = "envycontrol"
        elif "supergfxctl" in available:
            self.backend = "supergfxctl"
        elif "prime-select" in available:
            self.backend = "prime-select"
        elif "bios" in available:
            self.backend = "bios"
        else:
            self.backend = None

        logger.info(f"MUX backend: {self.backend or 'none'} (auto-detected)")

    def get_available_backends(self):
        backends = []
        if self.envycontrol:
            backends.append("envycontrol")
        if self.supergfxctl:
            backends.append("supergfxctl")
        if self.prime_select:
            backends.append("prime-select")
        if os.path.exists(_BIOS_MUX_PATH):
            backends.append("bios")
        return backends

    def set_backend(self, backend):
        available = self.get_available_backends()
        if backend in available:
            self.backend = backend
            # FIX: reset cache so next get_mode() reads fresh from new backend
            self._cached_mode = "unknown"
            self._last_check = 0.0
            logger.info(f"MUX backend switched to: {backend}")
            return True
        logger.warning(f"MUX backend '{backend}' not available (available: {available})")
        return False

    def is_available(self):
        return self.backend is not None

    def get_backend(self):
        return self.backend or "none"

    def get_mode(self):
        now = time.time()
        if now - self._last_check < 10.0:
            return self._cached_mode

        mode = "unknown"
        try:
            if self.backend == "bios":
                with open(_BIOS_MUX_PATH) as f:
                    val = int(f.read().strip())
                mode = _BIOS_MUX_READ.get(val, "unknown")
            elif self.backend == "envycontrol" and self.envycontrol:
                mode = subprocess.check_output(
                    [self.envycontrol, "--query"],
                    stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
            elif self.backend == "supergfxctl" and self.supergfxctl:
                mode = subprocess.check_output(
                    [self.supergfxctl, "-g"],
                    stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
            elif self.backend == "prime-select" and self.prime_select:
                mode = subprocess.check_output(
                    [self.prime_select, "query"],
                    stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
        except Exception as e:
            logger.debug(f"MUX get_mode error: {e}")

        self._cached_mode = mode
        self._last_check = now
        return mode

    def set_mode(self, mode):
        try:
            if self.backend == "bios":
                val = _BIOS_MUX_WRITE.get(mode)
                if val is None:
                    return f"Error: unknown mode '{mode}' for BIOS backend"
                with open(_BIOS_MUX_PATH, "w") as f:
                    f.write(str(val))

                time.sleep(0.1)
                try:
                    with open(_BIOS_MUX_PATH) as f:
                        readback = int(f.read().strip())
                    advanced_optimus = (readback == val)
                except Exception:
                    advanced_optimus = False

                self._cached_mode = mode
                self._last_check  = time.time()

                if advanced_optimus:
                    logger.info(f"MUX set to '{mode}' via BIOS sysfs (Advanced Optimus — no reboot needed)")
                    return "OK"
                else:
                    logger.info(f"MUX set to '{mode}' via BIOS sysfs (reboot required)")
                    return "OK_REBOOT_REQUIRED"

            elif self.backend == "envycontrol" and self.envycontrol:
                subprocess.run([self.envycontrol, "-s", mode], check=True, timeout=10)
                self._cached_mode = mode
                self._last_check  = time.time()
                return "OK"

            elif self.backend == "supergfxctl" and self.supergfxctl:
                m = {"hybrid": "Hybrid", "discrete": "Dedicated",
                     "integrated": "Integrated"}.get(mode, mode)
                subprocess.run([self.supergfxctl, "-m", m], check=True, timeout=10)
                self._cached_mode = mode
                self._last_check  = time.time()
                return "OK"

            elif self.backend == "prime-select" and self.prime_select:
                m = {"hybrid": "on-demand", "discrete": "nvidia",
                     "integrated": "intel"}.get(mode, mode)
                subprocess.run([self.prime_select, m], check=True, timeout=10)
                self._cached_mode = mode
                self._last_check  = time.time()
                return "OK"

        except Exception as e:
            return f"Error: {e}"
        return "No backend"


# ============================================================
# ANIMATION ENGINE
# ============================================================
class AnimationEngine(threading.Thread):
    FRAME_TIME       = 0.12
    FRAME_TIME_WAVE  = 0.15
    # Breathing/cycle were too jumpy at 0.5s; 0.12s stays smooth without heavy CPU use.
    FRAME_TIME_SLOW  = 0.12
    _COLOR_THRESHOLD = 3

    def __init__(self, rgb_ctrl):
        super().__init__(daemon=True)
        self.rgb = rgb_ctrl
        self.running = True
        self._last_uniform: tuple = (-1, -1, -1)
        self._last_wave: typing.List[typing.Tuple[int, int, int]] = [(-1, -1, -1)] * 8

    def _uniform_changed(self, new: tuple) -> bool:
        return any(abs(n - o) > self._COLOR_THRESHOLD
                   for n, o in zip(new, self._last_uniform))

    def _zone_changed(self, new: tuple, old: tuple) -> bool:
        return any(abs(n - o) > self._COLOR_THRESHOLD
                   for n, o in zip(new, old))

    def run(self):
        logger.info("Animation engine started")
        while self.running:
            # Pause animation during system sleep to avoid interfering with wake events
            if _system_sleeping.is_set():
                time.sleep(0.1)
                continue

            loop_start = time.time()
            with lock:
                pwr  = bool(state.get("power", True))
                mode = str(state.get("mode", "static"))
                bri  = float(state.get("brightness", 100)) / 100.0
                spd  = float(state.get("speed", 50))
                cols = [str(c) for c in state.get("colors", ["FF0000"] * 8)]
                d    = str(state.get("direction", "ltr"))

            if not pwr:
                self.rgb.write_brightness(False)
                self.rgb.write_all(["000000"] * 8)
                self._last_uniform = (-1, -1, -1)
                self._last_wave = [(-1, -1, -1)] * 8
                state_changed.clear()
                state_changed.wait()
                continue

            self.rgb.write_brightness(True)
            t = time.time()

            if mode == "static":
                targets = [self._hex_to_rgb(c) for c in cols]
                self.rgb.write_all([
                    f"{int(r * bri):02X}{int(g * bri):02X}{int(b * bri):02X}"
                    for r, g, b in targets
                ])
                self._last_uniform = (-1, -1, -1)
                self._last_wave = [(-1, -1, -1)] * 8
                state_changed.clear()
                state_changed.wait()
                continue

            elif mode == "breathing":
                period = 8.0 - (spd * 0.06)
                phase  = 0.1 + 0.9 * ((math.sin(2 * math.pi * t / period) + 1) / 2)
                base   = self._hex_to_rgb(cols[0])
                new_color = (
                    int(base[0] * phase * bri),
                    int(base[1] * phase * bri),
                    int(base[2] * phase * bri),
                )
                if self._uniform_changed(new_color):
                    self._last_uniform = new_color
                    hx = f"{new_color[0]:02X}{new_color[1]:02X}{new_color[2]:02X}"
                    self.rgb.write_all([hx] * 8)
                self._last_wave = [(-1, -1, -1)] * 8
                sleep_time = max(self.FRAME_TIME_SLOW - (time.time() - loop_start), 0.001)
                if state_changed.wait(timeout=sleep_time):
                    state_changed.clear()
                continue

            elif mode == "cycle":
                hue = (t * (spd * 0.003)) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, bri)
                new_color = (int(r * 255), int(g * 255), int(b * 255))
                if self._uniform_changed(new_color):
                    self._last_uniform = new_color
                    hx = f"{new_color[0]:02X}{new_color[1]:02X}{new_color[2]:02X}"
                    self.rgb.write_all([hx] * 8)
                self._last_wave = [(-1, -1, -1)] * 8
                sleep_time = max(self.FRAME_TIME_SLOW - (time.time() - loop_start), 0.001)
                if state_changed.wait(timeout=sleep_time):
                    state_changed.clear()
                continue

            elif mode == "wave":
                # Shift between user-selected base colors instead of HSV rainbow.
                base_cols = [self._hex_to_rgb(c) for c in cols[:4]]
                if not base_cols:
                    base_cols = [(255, 0, 0)]
                while len(base_cols) < 4:
                    base_cols.append(base_cols[-1])

                # Higher speed -> faster horizontal color shift.
                step_period = max(0.06, 0.42 - (spd * 0.0036))
                shift_pos = t / step_period
                shift_int = int(shift_pos)
                shift_frac = shift_pos - shift_int

                for i in range(8):
                    zone = i if d == "ltr" else (7 - i)
                    idx = (zone + shift_int) % 4
                    nxt = (idx + 1) % 4

                    c0 = base_cols[idx]
                    c1 = base_cols[nxt]

                    r = int((c0[0] + (c1[0] - c0[0]) * shift_frac) * bri)
                    g = int((c0[1] + (c1[1] - c0[1]) * shift_frac) * bri)
                    b = int((c0[2] + (c1[2] - c0[2]) * shift_frac) * bri)
                    new_color = (r, g, b)

                    if self._zone_changed(new_color, self._last_wave[i]):
                        self._last_wave[i] = new_color
                        self.rgb.write_zone(i, f"{new_color[0]:02X}{new_color[1]:02X}{new_color[2]:02X}")
                self._last_uniform = (-1, -1, -1)
                sleep_time = max(self.FRAME_TIME_WAVE - (time.time() - loop_start), 0.001)
                if state_changed.wait(timeout=sleep_time):
                    state_changed.clear()
                continue

            sleep_time = max(self.FRAME_TIME - (time.time() - loop_start), 0.001)
            if state_changed.wait(timeout=sleep_time):
                state_changed.clear()

    def _hex_to_rgb(self, h):
        h = str(h).lstrip("#")
        if not h or len(h) < 6:
            logger.warning(f"Invalid hex color: '{h}', falling back to red")
            return (255, 0, 0)
        try:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError as e:
            logger.error(f"Hex conversion error for '{h}': {e}")
            return (255, 0, 0)


# ============================================================
# STATE
# ============================================================
state: typing.Dict[str, typing.Any] = {
    "mode":          "static",
    "colors":        ["FF0000"] * 8,
    "speed":         50,
    "brightness":    100,
    "direction":     "ltr",
    "power":         True,
    "fan_mode":      "auto",
    "power_profile": "balanced",
    "win_lock":      False,
    "prtsc_fix":     False,
    "f1_fix":        False,
    "mux_backend":   "auto",
}

fan_ctrl   = FanController()
rgb_ctrl   = RGBController()
power_ctrl = PowerProfileController()
mux_ctrl   = MUXController()
engine     = AnimationEngine(rgb_ctrl)


def save_state():
    with lock:
        try:
            snapshot = copy.deepcopy(state)
        except Exception as e:
            logger.error(f"State snapshot error: {e}")
            return
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        temp_file = f"{CONFIG_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(snapshot, f)
        os.replace(temp_file, CONFIG_FILE)
    except Exception as e:
        logger.error(f"State save error: {e}")
    finally:
        state_changed.set()


def load_state():
    with lock:
        try:
            if not os.path.exists(CONFIG_FILE):
                return
            with open(CONFIG_FILE) as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                return

            if loaded.get("mode") in VALID_LIGHT_MODES:
                state["mode"] = loaded["mode"]

            colors = loaded.get("colors")
            if isinstance(colors, list):
                cleaned: typing.List[str] = []
                for i, c in enumerate(colors):
                    if i >= 8:
                        break
                    c_str = str(c).lstrip("#").upper()
                    if HEX_COLOR_RE.match(c_str):
                        cleaned.append(c_str)
                if cleaned:
                    c0 = cleaned[0]
                    state["colors"] = (cleaned + [c0] * 8)[:8]

            speed = loaded.get("speed")
            if isinstance(speed, int):
                state["speed"] = max(1, min(speed, 100))

            brightness = loaded.get("brightness")
            if isinstance(brightness, int):
                state["brightness"] = max(0, min(brightness, 100))

            if loaded.get("direction") in VALID_DIRECTIONS:
                state["direction"] = loaded["direction"]

            if isinstance(loaded.get("power"), bool):
                state["power"] = loaded["power"]

            fm = loaded.get("fan_mode")
            if fm in ("auto", "max", "custom"):
                state["fan_mode"] = fm

            pp = loaded.get("power_profile")
            if isinstance(pp, str) and pp in ("power-saver", "balanced", "performance"):
                state["power_profile"] = pp

            if isinstance(loaded.get("prtsc_fix"), bool):
                state["prtsc_fix"] = loaded["prtsc_fix"]
            if isinstance(loaded.get("f1_fix"), bool):
                state["f1_fix"] = loaded["f1_fix"]
            if isinstance(loaded.get("win_lock"), bool):
                state["win_lock"] = loaded["win_lock"]

            mb = loaded.get("mux_backend")
            if isinstance(mb, str):
                state["mux_backend"] = mb

        except Exception as e:
            logger.error(f"State load error: {e}")


# ============================================================
# D-BUS SERVICE
# ============================================================
class HPManagerService(object):
    """
    <node>
      <interface name="com.yyl.hpmanager">
        <method name="SetColor"><arg type="i" name="z" direction="in"/><arg type="s" name="h" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="SetMode"><arg type="s" name="m" direction="in"/><arg type="i" name="s" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="SetGlobal"><arg type="b" name="p" direction="in"/><arg type="i" name="b" direction="in"/><arg type="s" name="d" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="GetState"><arg type="s" name="j" direction="out"/></method>
        <method name="SetFanMode"><arg type="s" name="mode" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="SetFanTarget"><arg type="i" name="fan" direction="in"/><arg type="i" name="rpm" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="GetFanInfo"><arg type="s" name="j" direction="out"/></method>
        <method name="SetPowerProfile"><arg type="s" name="profile" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="GetPowerProfile"><arg type="s" name="j" direction="out"/></method>
        <method name="SetGpuMode"><arg type="s" name="mode" direction="in"/><arg type="s" name="result" direction="out"/></method>
        <method name="GetGpuInfo"><arg type="s" name="j" direction="out"/></method>
        <method name="GetSystemInfo"><arg type="s" name="j" direction="out"/></method>
        <method name="CleanMemory"><arg type="s" name="result" direction="out"/></method>
        <method name="SetWinLock"><arg type="b" name="locked" direction="in"/><arg type="s" name="result" direction="out"/></method>
        <method name="SetKeyboardFixes"><arg type="b" name="prtsc" direction="in"/><arg type="b" name="f1" direction="in"/><arg type="s" name="result" direction="out"/></method>
        <method name="SetMuxBackend"><arg type="s" name="backend" direction="in"/><arg type="s" name="result" direction="out"/></method>
      </interface>
    </node>
    """

    def __init__(self):
        self._static_info = {
            "hostname":     platform.node(),
            "kernel":       platform.release(),
            "os_name":      "Linux",
            "product_name": "HP Laptop",
        }
        for dmi_file in ("/sys/devices/virtual/dmi/id/product_name",
                         "/sys/devices/virtual/dmi/id/product_family"):
            if os.path.exists(dmi_file):
                try:
                    with open(dmi_file) as f:
                        self._static_info["product_name"] = f.read().strip()
                    break
                except Exception:
                    pass

        self._has_nvidia_smi = shutil.which("nvidia-smi") is not None

        self._cpu_temp_path: typing.Optional[str] = None
        self._gpu_temp_path: typing.Optional[str] = None
        self._find_temp_paths()

        self._last_nv_time: float = 0.0
        self._nv_temp_cache: float = 0.0
        self._nv_fail_cooldown: float = 0.0

        self._info_cache: typing.Dict[str, typing.Any] = {}
        self._fan_cache:  typing.Dict[str, typing.Any] = {}
        self._gpu_cache: typing.Dict[str, typing.Any] = {
            "available":          mux_ctrl.is_available(),
            "backend":            mux_ctrl.get_backend(),
            "available_backends": mux_ctrl.get_available_backends(),
            "mode":               "unknown",
        }

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._setup_sleep_handler, daemon=True).start()

    def _setup_sleep_handler(self):
        """Listen to system sleep/wake events via logind."""
        try:
            bus = SystemBus()
            logind = bus.get("org.freedesktop.login1", "/org/freedesktop/login1/Manager")
            logind.onPropertiesChanged += self._on_sleep_state_changed
            logger.info("Sleep/wake event handler registered")
        except Exception as e:
            logger.warning(f"Failed to register sleep/wake handler: {e}")

    def _on_sleep_state_changed(self, interface_name, changed_properties, invalidated_properties):
        """Handle system sleep/wake transitions."""
        try:
            if "PrepareForSleep" in changed_properties:
                preparing = changed_properties["PrepareForSleep"]
                if preparing:
                    logger.info("System preparing for sleep - pausing daemon operations")
                    _system_sleeping.set()
                else:
                    logger.info("System waking up - resuming daemon operations after delay")
                    _system_sleeping.clear()
                    # Give system 2 seconds to fully restore before resuming operations
                    def _delay_resume():
                        time.sleep(2.0)
                        state_changed.set()
                    threading.Thread(target=_delay_resume, daemon=True).start()
        except Exception as e:
            logger.debug(f"Sleep state change handler error: {e}")

    def _monitor_loop(self):
        """Background thread — collects sensor data to avoid blocking D-Bus calls."""
        _mux_last_poll: float = 0.0
        _MUX_POLL_INTERVAL = 30.0

        while True:
            # Skip updates during system sleep to avoid interfering with wake events
            if _system_sleeping.is_set():
                time.sleep(0.5)
                continue

            info = self._static_info.copy()
            info["cpu_temp"] = self._get_real_cpu_temp()
            info["gpu_temp"] = self._get_real_gpu_temp()

            fans_data = {
                str(i): {
                    "current": fan_ctrl.get_current_speed(i),
                    "max":     fan_ctrl.get_max_speed(i),
                    "target":  fan_ctrl.get_target_speed(i),
                }
                for i in fan_ctrl.found_fans
            }
            fan_snapshot = {
                "available": fan_ctrl.is_available(),
                "fan_count": fan_ctrl.get_fan_count(),
                "mode":      fan_ctrl.get_mode(),
                "fans":      fans_data,
            }

            now = time.time()
            if now - _mux_last_poll >= _MUX_POLL_INTERVAL:
                with lock:
                    forced_backend = state.get("mux_backend", "auto")
                gpu_snapshot = {
                    "available":          mux_ctrl.is_available(),
                    "backend":            mux_ctrl.get_backend(),
                    "available_backends": mux_ctrl.get_available_backends(),
                    # FIX: include forced_backend in cache so GetGpuInfo is always consistent
                    "forced_backend":     forced_backend,
                    "mode":               mux_ctrl.get_mode(),
                }
                _mux_last_poll = now
            else:
                with _cache_lock:
                    gpu_snapshot = dict(self._gpu_cache)
                # FIX: always refresh forced_backend from live state (it can change via SetMuxBackend)
                with lock:
                    gpu_snapshot["forced_backend"] = state.get("mux_backend", "auto")

            with _cache_lock:
                self._info_cache = info
                self._fan_cache  = fan_snapshot
                self._gpu_cache  = gpu_snapshot

            time.sleep(2.0)

    def _find_temp_paths(self):
        best_score = -1000
        RANK_DRV = {"zenpower": 100, "coretemp": 90, "k10temp": 90,
                    "cpu_thermal": 80, "hp_wmi": 60, "acpitz": 30}
        RANK_LBL = {"tdie": 100, "package id 0": 95, "tctl": 90, "core": 80, "composite": 50}
        try:
            for d in os.listdir("/sys/class/hwmon"):
                path = os.path.join("/sys/class/hwmon", d)
                try:
                    with open(os.path.join(path, "name")) as f:
                        drv = f.read().strip().lower()
                except Exception:
                    continue
                d_score = RANK_DRV.get(drv, 10)
                for tf in glob.glob(os.path.join(path, "temp*_input")):
                    label = ""
                    lp = tf.replace("_input", "_label")
                    if os.path.exists(lp):
                        try:
                            with open(lp) as f:
                                label = f.read().strip().lower()
                        except Exception:
                            pass
                    l_score = max((v for k, v in RANK_LBL.items() if k in label), default=0)
                    score = d_score + l_score - (500 if "75" in str(tf) else 0)
                    if score > best_score:
                        best_score = score
                        self._cpu_temp_path = tf
        except Exception:
            pass

        try:
            for d in os.listdir("/sys/class/hwmon"):
                path = os.path.join("/sys/class/hwmon", d)
                try:
                    with open(os.path.join(path, "name")) as f:
                        name = f.read().strip().lower()
                    if name in ("amdgpu", "i915", "nouveau"):
                        self._gpu_temp_path = os.path.join(path, "temp1_input")
                except Exception:
                    continue
        except Exception:
            pass

    # ── D-Bus methods ────────────────────────────────────────────────────────

    def SetColor(self, z, h):
        c = str(h).lstrip("#").upper()
        if not HEX_COLOR_RE.match(c):
            return "FAIL"
        with lock:
            state["mode"]  = "static"
            state["power"] = True
            if z == 8:
                state["colors"] = [c] * 8
            elif 0 <= z < 8:
                state["colors"][z] = c
            else:
                return "FAIL"
        save_state()
        return "OK"

    def SetMode(self, m, s):
        if m not in VALID_LIGHT_MODES:
            return "FAIL"
        with lock:
            state["mode"]  = m
            state["speed"] = max(1, min(int(s), 100))
            state["power"] = True
        save_state()
        return "OK"

    def SetGlobal(self, p, b, d):
        if d not in VALID_DIRECTIONS:
            return "FAIL"
        with lock:
            state["power"]      = bool(p)
            state["brightness"] = max(0, min(int(b), 100))
            state["direction"]  = d
        save_state()
        return "OK"

    def GetState(self):
        with lock:
            return json.dumps(state)

    def SetFanMode(self, mode):
        logger.info(f"SetFanMode: {mode}")
        ok = fan_ctrl.set_mode(mode)
        if ok:
            with lock:
                state["fan_mode"] = mode
            save_state()
        return "OK" if ok else "FAIL"

    def SetFanTarget(self, fan, rpm):
        logger.info(f"SetFanTarget: fan={fan}, rpm={rpm}")
        return "OK" if fan_ctrl.set_fan_target(fan, rpm) else "FAIL"

    def GetFanInfo(self):
        with _cache_lock:
            return json.dumps(self._fan_cache)

    def SetPowerProfile(self, profile):
        if profile not in power_ctrl.get_profiles():
            return "FAIL"
        ok = power_ctrl.set_profile(profile)
        if ok:
            with lock:
                state["power_profile"] = profile
            save_state()
        return "OK" if ok else "FAIL"

    def GetPowerProfile(self):
        return json.dumps({
            "available": power_ctrl.available,
            "active":    power_ctrl.get_active(),
            "profiles":  power_ctrl.get_profiles(),
        })

    def SetGpuMode(self, mode):
        if mode not in VALID_GPU_MODES:
            return "FAIL"
        result = mux_ctrl.set_mode(mode)
        # FIX: update cache immediately so next GetGpuInfo reflects new mode
        if result in ("OK", "OK_REBOOT_REQUIRED"):
            with _cache_lock:
                self._gpu_cache["mode"] = mode
        return result

    def GetGpuInfo(self):
        with _cache_lock:
            data = dict(self._gpu_cache)
        # Always read forced_backend live from state (already in cache but keep fresh)
        with lock:
            data["forced_backend"] = state.get("mux_backend", "auto")
        return json.dumps(data)

    def GetSystemInfo(self):
        with _cache_lock:
            return json.dumps(self._info_cache)

    def _get_real_cpu_temp(self):
        if self._cpu_temp_path and os.path.exists(self._cpu_temp_path):
            try:
                with open(self._cpu_temp_path) as f:
                    return int(f.read().strip()) / 1000.0
            except Exception:
                pass
        return 0.0

    def _get_real_gpu_temp(self):
        if self._gpu_temp_path and os.path.exists(self._gpu_temp_path):
            try:
                with open(self._gpu_temp_path) as f:
                    return int(f.read().strip()) / 1000.0
            except Exception:
                pass

        if self._has_nvidia_smi:
            now = time.time()
            if now < self._nv_fail_cooldown:
                return self._nv_temp_cache
            if now - self._last_nv_time > 5.0:
                self._last_nv_time = now
                try:
                    out = subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=temperature.gpu",
                         "--format=csv,noheader,nounits"],
                        stderr=subprocess.DEVNULL, timeout=1.0
                    ).decode().strip()
                    self._nv_temp_cache = float(out)
                except Exception:
                    self._nv_fail_cooldown = now + 15.0
            return self._nv_temp_cache

        return 0.0

    def CleanMemory(self):
        try:
            subprocess.run(["sync"], check=True, timeout=5)
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    def SetWinLock(self, locked):
        logger.info(f"SetWinLock: {'LOCKED' if locked else 'UNLOCKED'}")
        with lock:
            state["win_lock"] = bool(locked)
        rgb_ctrl.write_win_lock(bool(locked))
        save_state()
        return "OK"

    def SetKeyboardFixes(self, prtsc, f1):
        logger.info(f"SetKeyboardFixes: prtsc={prtsc}, f1={f1}")
        with lock:
            state["prtsc_fix"] = bool(prtsc)
            state["f1_fix"]    = bool(f1)
        self._write_hwdb_rules(prtsc, f1)
        save_state()
        return "OK"

    def _write_hwdb_rules(self, prtsc, f1):
        hwdb_path = "/etc/udev/hwdb.d/90-hp-keyboard-fixes.hwdb"

        if not prtsc and not f1:
            if os.path.exists(hwdb_path):
                try:
                    os.remove(hwdb_path)
                    subprocess.run(["systemd-hwdb", "update"], capture_output=True)
                    subprocess.run(["udevadm", "trigger", "-s", "input"], capture_output=True)
                except Exception:
                    pass
            return

        content = [
            "# HP Keyboard Fixes - Generated by OMEN Command Center for Linux",
            "evdev:atkbd:dmi:bvn*:bvr*:bd*:svnHP*:pn*:*",
        ]
        if prtsc:
            content.append(" KEYBOARD_KEY_b7=sysrq")
        if f1:
            content.append(" KEYBOARD_KEY_ab=f1")

        new_content = "\n".join(content) + "\n"

        if os.path.exists(hwdb_path):
            try:
                with open(hwdb_path, "r") as f:
                    if f.read() == new_content:
                        return
            except Exception:
                pass

        try:
            os.makedirs(os.path.dirname(hwdb_path), exist_ok=True)
            with open(hwdb_path, "w") as f:
                f.write(new_content)

            def _apply():
                try:
                    subprocess.run(["systemd-hwdb", "update"], check=True)
                    subprocess.run(["udevadm", "trigger", "-s", "input"], check=True)
                    logger.info("Keyboard fixes applied via hwdb successfully")
                except Exception as e:
                    logger.error(f"Failed to apply hwdb: {e}")

            threading.Thread(target=_apply, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to write hwdb rules: {e}")
        return "OK"

    def SetMuxBackend(self, backend):
        logger.info(f"SetMuxBackend: {backend}")

        if backend == "auto":
            with lock:
                state["mux_backend"] = "auto"
            save_state()
            # Re-detect best backend after clearing forced selection
            mux_ctrl._detect_backend()
            # FIX: update cache immediately
            with _cache_lock:
                self._gpu_cache["backend"]        = mux_ctrl.get_backend()
                self._gpu_cache["forced_backend"] = "auto"
            return "OK"

        if mux_ctrl.set_backend(backend):
            with lock:
                state["mux_backend"] = backend
            save_state()
            # FIX: update cache immediately so UI reflects change without waiting 30s
            with _cache_lock:
                self._gpu_cache["backend"]        = backend
                self._gpu_cache["forced_backend"] = backend
                self._gpu_cache["mode"]           = "unknown"  # will refresh on next poll
            return "OK"

        return "FAIL"


# ============================================================
# MAIN
# ============================================================
def main():
    if os.geteuid() != 0:
        print("Root privileges required (sudo).")
        sys.exit(1)

    load_state()

    # Re-detect MUX backend now that state is loaded (forced_backend may be set)
    mux_ctrl._detect_backend()

    if fan_ctrl.is_available():
        saved_fan = state.get("fan_mode", "auto")
        if saved_fan == "custom":
            saved_fan = "auto"
            state["fan_mode"] = "auto"
            logger.warning("Custom fan mode not restorable (no saved targets), falling back to auto")

        if saved_fan in ("auto", "max"):
            if fan_ctrl.get_mode() != saved_fan:
                ok = fan_ctrl.set_mode(saved_fan)
                logger.info(f"Restored fan mode '{saved_fan}' (success={ok})")
            else:
                logger.info(f"Fan mode already '{saved_fan}', skipping write.")

    if power_ctrl.available:
        saved_pp = state.get("power_profile", "balanced")
        if saved_pp in power_ctrl.get_profiles():
            if power_ctrl.get_active() != saved_pp:
                ok = power_ctrl.set_profile(saved_pp)
                logger.info(f"Restored power profile '{saved_pp}' (success={ok})")
            else:
                logger.info(f"Power profile already '{saved_pp}', skipping.")

    service = HPManagerService()

    if state.get("prtsc_fix") or state.get("f1_fix"):
        service.SetKeyboardFixes(state.get("prtsc_fix"), state.get("f1_fix"))

    if rgb_ctrl.is_available():
        rgb_ctrl.write_win_lock(state.get("win_lock", False))
        engine.start()
        logger.info("RGB engine started")

    try:
        bus = SystemBus()
        bus.publish("com.yyl.hpmanager", service)
        logger.info("HP Manager Daemon ready on D-Bus")
        if fan_ctrl.is_available():
            logger.info(f"Fan control active: {fan_ctrl.get_fan_count()} fans")
        if power_ctrl.available:
            logger.info(f"Power profiles: {power_ctrl.get_profiles()}")
        if mux_ctrl.is_available():
            logger.info(f"MUX backend: {mux_ctrl.get_backend()}")
        GLib.MainLoop().run()
    except Exception as e:
        logger.critical(f"Service error: {e}")


if __name__ == "__main__":
    main()
