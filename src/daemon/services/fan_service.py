#!/usr/bin/env python3
"""OMEN Command Center for Linux — Fan Microservice.

Owns fan speed monitoring, fan mode control (auto/max/custom), and per-fan
RPM target setting.  Exposes its functionality over D-Bus as
``com.yyl.hpmanager.fan``.
"""

import glob
import os
import sys
import threading
import time

# Ensure the parent package is importable when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.logging_config import setup_logging
from common.config import ServiceConfig
from common.sysfs import sysfs_read, sysfs_read_str, sysfs_write, sysfs_exists
from common.dbus_helpers import run_service, system_sleeping

logger = setup_logging("fan")

PWM_MAX = 255
PWM_FALLBACK_MIN = 220
THERMAL_PROFILE_BALANCED = 0
THERMAL_PROFILE_MAX = 1

# ─── Fan Controller ───────────────────────────────────────────────────────────


class FanController:
    """Low-level fan hardware access via hwmon sysfs."""

    def __init__(self):
        self.hwmon_path = self._find_hwmon()
        self.fan_count = 0
        self.found_fans = []
        self.max_speeds = {}
        self.mode = "auto"
        self._fallback_paths = {}
        if self.hwmon_path:
            self._detect_fans()
            self._read_max_speeds()
            self._read_current_mode()

    # ── discovery ─────────────────────────────────────────────────────

    def _find_hwmon(self):
        for path in glob.glob("/sys/class/hwmon/hwmon*/name"):
            try:
                with open(path) as f:
                    name = f.read().strip()
                    if name in ("hp", "hp-omen"):
                        hwmon = os.path.dirname(path)
                        logger.info("Found HP/OMEN hwmon at %s (driver=%s)", hwmon, name)
                        return hwmon
            except Exception:
                pass

        for platform_name in ("hp-wmi", "hp_wmi", "hp-omen"):
            platform_hwmon = f"/sys/devices/platform/{platform_name}/hwmon"
            if os.path.exists(platform_hwmon):
                try:
                    entries = sorted(os.listdir(platform_hwmon))
                    if entries:
                        path = os.path.join(platform_hwmon, entries[0])
                        logger.info("Found HP hwmon via platform device at %s", path)
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
                    fan_num = int(f[3:-6])
                    self.found_fans.append(fan_num)
                    self._fallback_paths[fan_num] = self._find_fallback_path(fan_num)
                except ValueError:
                    continue
        self.found_fans.sort()
        self.fan_count = len(self.found_fans)

    def _find_fallback_path(self, fan_num):
        for path in glob.glob("/sys/class/hwmon/hwmon*/fan*_input"):
            try:
                basename = os.path.basename(path)
                hwmon_dir = os.path.dirname(path)
                if hwmon_dir == self.hwmon_path:
                    continue
                idx = basename.replace("fan", "").replace("_input", "")
                if idx == str(fan_num):
                    return path
            except Exception:
                continue
        return None

    def _read_max_speeds(self):
        if not self.hwmon_path:
            return
        for i in self.found_fans:
            max_path = os.path.join(self.hwmon_path, f"fan{i}_max")
            self.max_speeds[i] = sysfs_read(max_path, 6000)

    def _read_current_mode(self):
        if not self.hwmon_path:
            return
        pwm_path = os.path.join(self.hwmon_path, "pwm1_enable")
        val = sysfs_read(pwm_path, 2)
        if val == 0:
            self.mode = "max"
            return
        if val == 1:
            self.mode = "custom"
            return
        self.mode = self._read_mode_fallback()

    def _read_mode_fallback(self):
        for path in (
            "/sys/devices/platform/hp-wmi/thermal_profile",
            "/sys/devices/platform/hp-omen/thermal_profile",
        ):
            if not sysfs_exists(path):
                continue
            return "max" if sysfs_read(path, THERMAL_PROFILE_BALANCED) == THERMAL_PROFILE_MAX else "auto"

        for path in (
            "/sys/firmware/acpi/platform_profile",
            "/sys/devices/platform/hp-wmi/platform_profile",
        ):
            if not sysfs_exists(path):
                continue
            raw = sysfs_read_str(path, "balanced").strip().lower()
            return "max" if "performance" in raw else "auto"

        return "auto"

    # ── read ──────────────────────────────────────────────────────────

    def _hwmon_read(self, filename):
        if not self.hwmon_path:
            return 0
        return sysfs_read(os.path.join(self.hwmon_path, filename))

    def get_fan_count(self):
        return self.fan_count

    def get_max_speed(self, fan_num):
        return self.max_speeds.get(fan_num, 6000)

    def get_current_speed(self, fan_num):
        speed = self._hwmon_read(f"fan{fan_num}_input")
        if speed == 0:
            speed = self._try_fan_speed_fallback(fan_num)
        return speed

    def _try_fan_speed_fallback(self, fan_num):
        path = self._fallback_paths.get(fan_num)
        if path:
            val = sysfs_read(path)
            if val > 0:
                return val
        return 0

    def get_target_speed(self, fan_num):
        target_path = os.path.join(self.hwmon_path, f"fan{fan_num}_target") if self.hwmon_path else None
        if target_path and sysfs_exists(target_path):
            return sysfs_read(target_path)

        if self._has_pwm_fallback():
            pwm = self._hwmon_read("pwm1")
            return int(self.get_max_speed(fan_num) * pwm / PWM_MAX)

        return 0

    # ── write ─────────────────────────────────────────────────────────

    def set_mode(self, mode):
        if not self.hwmon_path:
            return False
        val = {"auto": 2, "max": 0, "custom": 1}.get(mode)
        if val is None:
            return False

        if self.get_mode() == mode:
            logger.info("Fan mode already %s, skipping write", mode)
            return True

        ok = sysfs_write(os.path.join(self.hwmon_path, "pwm1_enable"), val)

        if not ok and mode == "max":
            for profile_path, profile_value in (
                ("/sys/devices/platform/hp-wmi/thermal_profile", "1"),
                ("/sys/devices/platform/hp-omen/thermal_profile", "1"),
                ("/sys/firmware/acpi/platform_profile", "performance"),
                ("/sys/devices/platform/hp-wmi/platform_profile", "performance"),
            ):
                if not sysfs_exists(profile_path):
                    continue
                if sysfs_write(profile_path, profile_value):
                    ok = True
                    break

        if ok:
            self.mode = mode
            logger.info("Fan mode set to %s", mode)
        return ok

    def set_fan_target(self, fan_num, rpm):
        if not self.hwmon_path or fan_num not in self.found_fans:
            return False
        rpm = max(0, min(rpm, self.get_max_speed(fan_num)))
        path = os.path.join(self.hwmon_path, f"fan{fan_num}_target")
        if sysfs_exists(path):
            ok = sysfs_write(path, rpm)
        elif self._has_pwm_fallback():
            ok = self._set_pwm_fallback_target(fan_num, rpm)
        else:
            logger.warning(
                "No fan%d_target or pwm1 fallback available under %s",
                fan_num,
                self.hwmon_path,
            )
            return False

        if ok:
            logger.info("Fan %d target set to %d RPM", fan_num, rpm)
        return ok

    def _has_pwm_fallback(self):
        if not self.hwmon_path:
            return False
        return sysfs_exists(os.path.join(self.hwmon_path, "pwm1"))

    def _set_pwm_fallback_target(self, fan_num, rpm):
        max_speed = self.get_max_speed(fan_num)
        if max_speed <= 0:
            max_speed = 6000

        pwm = int(round(rpm * PWM_MAX / max_speed))
        pwm = max(0, min(pwm, PWM_MAX))
        if pwm > 0:
            pwm = max(pwm, PWM_FALLBACK_MIN)

        enable_path = os.path.join(self.hwmon_path, "pwm1_enable")
        if sysfs_exists(enable_path) and self.get_mode() != "custom":
            if not self.set_mode("custom"):
                return False

        return sysfs_write(os.path.join(self.hwmon_path, "pwm1"), pwm)

    def is_available(self):
        return self.hwmon_path is not None and self.fan_count > 0

    def get_mode(self):
        if self.hwmon_path:
            self._read_current_mode()
        return self.mode


# ─── D-Bus Service ────────────────────────────────────────────────────────────

import json


class FanService:
    """
    <node>
      <interface name="com.yyl.hpmanager.fan">
        <method name="SetFanMode"><arg type="s" name="mode" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="SetFanTarget"><arg type="i" name="fan" direction="in"/><arg type="i" name="rpm" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="GetFanInfo"><arg type="s" name="j" direction="out"/></method>
        <method name="Ping"><arg type="s" name="resp" direction="out"/></method>
      </interface>
    </node>
    """

    def __init__(self):
        self._fan = FanController()
        self._config = ServiceConfig("fan", {"fan_mode": "auto"})
        self._config.load()

        self._cache_lock = threading.Lock()
        self._fan_cache = {}

        # Restore saved fan mode
        self._restore_fan_mode()

        # Background monitoring thread
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _restore_fan_mode(self):
        if not self._fan.is_available():
            return
        saved = self._config.get("fan_mode", "auto")
        if saved == "custom":
            saved = "auto"
            self._config.set("fan_mode", "auto")
            logger.warning("Custom fan mode not restorable, falling back to auto")

        if saved in ("auto", "max"):
            if self._fan.get_mode() != saved:
                ok = self._fan.set_mode(saved)
                logger.info("Restored fan mode '%s' (success=%s)", saved, ok)
            else:
                logger.info("Fan mode already '%s', skipping write", saved)

    def _monitor_loop(self):
        while True:
            if system_sleeping.is_set():
                time.sleep(0.5)
                continue

            fans_data = {
                str(i): {
                    "current": self._fan.get_current_speed(i),
                    "max": self._fan.get_max_speed(i),
                    "target": self._fan.get_target_speed(i),
                }
                for i in self._fan.found_fans
            }
            snapshot = {
                "available": self._fan.is_available(),
                "fan_count": self._fan.get_fan_count(),
                "mode": self._fan.get_mode(),
                "fans": fans_data,
            }

            with self._cache_lock:
                self._fan_cache = snapshot

            time.sleep(2.0)

    # ── D-Bus methods ─────────────────────────────────────────────────

    def SetFanMode(self, mode):
        logger.info("SetFanMode: %s", mode)
        ok = self._fan.set_mode(mode)
        if ok:
            self._config.set("fan_mode", mode)
            self._config.save()
        return "OK" if ok else "FAIL"

    def SetFanTarget(self, fan, rpm):
        logger.info("SetFanTarget: fan=%d, rpm=%d", fan, rpm)
        return "OK" if self._fan.set_fan_target(fan, rpm) else "FAIL"

    def GetFanInfo(self):
        with self._cache_lock:
            return json.dumps(self._fan_cache)

    def Ping(self):
        return "OK"


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    service = FanService()
    if service._fan.is_available():
        logger.info("Fan control active: %d fans", service._fan.get_fan_count())
    run_service("com.yyl.hpmanager.fan", service, service_name="fan")


if __name__ == "__main__":
    main()
