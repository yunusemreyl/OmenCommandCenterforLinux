#!/usr/bin/env python3
"""OMEN Command Center for Linux — Power Profile Microservice.

Owns power-profile management (PPD / Tuned / OMEN Direct) and NVIDIA
GPU power-limit synchronisation.  Exposes its functionality over D-Bus
as ``com.yyl.hpmanager.power``.
"""

import json
import os
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.logging_config import setup_logging
from common.config import ServiceConfig
from common.dbus_helpers import run_service
from common.sysfs import (
    normalize_profile_name,
    sysfs_exists,
    sysfs_read,
    sysfs_read_str,
    sysfs_write,
)

from pydbus import SystemBus

logger = setup_logging("power")
THERMAL_PROFILE_BALANCED = 0


# ─── Power Profile Controller ────────────────────────────────────────────────


class PowerProfileController:
    PPD_BUS = "net.hadess.PowerProfiles"
    PPD_PATH = "/net/hadess/PowerProfiles"
    TUNED_BUS = "com.redhat.tuned"
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
                if sysfs_exists("/sys/devices/platform/hp-wmi/thermal_profile") or \
                   sysfs_exists("/sys/devices/platform/hp-omen/thermal_profile"):
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
                if "powersave" in tp:
                    return "power-saver"
                if "performance" in tp:
                    return "performance"
                return "balanced"
            # omen_direct
            return self._get_omen_direct_active()
        except Exception:
            return "balanced"

    def _get_omen_direct_active(self):
        for path in (
            "/sys/firmware/acpi/platform_profile",
            "/sys/devices/platform/hp-wmi/platform_profile",
        ):
            if not sysfs_exists(path):
                continue
            normalized = normalize_profile_name(sysfs_read_str(path, "balanced"))
            if "performance" in normalized:
                return "performance"
            if normalized in ("low-power", "quiet", "cool", "power-saver"):
                return "power-saver"
            return "balanced"

        for path in (
            "/sys/devices/platform/hp-wmi/thermal_profile",
            "/sys/devices/platform/hp-omen/thermal_profile",
        ):
            if not sysfs_exists(path):
                continue
            val = sysfs_read(path, THERMAL_PROFILE_BALANCED)
            if val == 1:
                return "performance"
            return "balanced"

        return "balanced"

    def _sync_omen_profile(self, profile):
        target_candidates = {
            "performance": ("performance",),
            "balanced": ("balanced",),
            "power-saver": ("low-power", "quiet", "cool", "power-saver", "balanced"),
        }.get(profile, ("balanced",))

        for path in (
            "/sys/firmware/acpi/platform_profile",
            "/sys/devices/platform/hp-wmi/platform_profile",
        ):
            if not sysfs_exists(path):
                continue
            choices_raw = sysfs_read_str(f"{path}_choices", "")
            choices = {
                normalize_profile_name(token.strip("[]"))
                for token in choices_raw.split()
                if token.strip("[]")
            }
            target = "balanced"
            for candidate in target_candidates:
                if not choices or candidate in choices:
                    target = candidate
                    break
            if sysfs_write(path, target):
                return True
            return False

        thermal_val = {"power-saver": "0", "balanced": "0", "performance": "1"}.get(
            profile, "0"
        )
        for path in (
            "/sys/devices/platform/hp-wmi/thermal_profile",
            "/sys/devices/platform/hp-omen/thermal_profile",
        ):
            if not sysfs_exists(path):
                continue
            if sysfs_write(path, thermal_val):
                return True
            return False
        return False

    def set_profile(self, profile):
        if not self.available:
            return False
        try:
            if self.mode == "ppd":
                self.proxy.ActiveProfile = profile
            elif self.mode == "tuned":
                mapping = {
                    "power-saver": "powersave",
                    "balanced": "balanced",
                    "performance": "throughput-performance",
                }
                self.proxy.switch_profile(mapping.get(profile, "balanced"))
            elif self.mode == "omen_direct":
                if not self._sync_omen_profile(profile):
                    return False

            threading.Thread(
                target=self._sync_hardware_power, args=(profile,), daemon=True
            ).start()
            return True
        except Exception as e:
            logger.error("Power profile set error (%s): %s", self.mode, e)
            return False

    def _sync_nvidia_power(self, profile):
        try:
            if not shutil.which("nvidia-smi"):
                return

            if profile == "performance":
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=power.max_limit",
                        "--format=csv,noheader,nounits",
                    ],
                    timeout=2.0,
                ).decode().strip()
                if out:
                    limit = int(float(out))
                    subprocess.run(
                        ["nvidia-smi", "-pl", str(limit)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2.0,
                    )
                    logger.info("NVIDIA GPU locked to MAX Performance: %dW", limit)
            else:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=power.default_limit",
                        "--format=csv,noheader,nounits",
                    ],
                    timeout=2.0,
                ).decode().strip()
                if out:
                    limit = int(float(out))
                    subprocess.run(
                        ["nvidia-smi", "-pl", str(limit)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2.0,
                    )
                    logger.info("NVIDIA GPU restored to DEFAULT Base: %dW", limit)
        except Exception as e:
            logger.warning("Failed to sync NVIDIA power curve: %s", e)

    def _sync_hardware_power(self, profile):
        """Orchestrate NVIDIA SMI and Kernel WMI power limits."""
        self._sync_omen_profile(profile)
        self._sync_nvidia_power(profile)
        self._sync_kernel_gpu_power(profile)

    def _sync_kernel_gpu_power(self, profile):
        """Trigger TGP and PPAB via the patched hp-wmi driver."""
        base = "/sys/devices/platform/hp-wmi"
        if not sysfs_exists(base):
            base = "/sys/devices/platform/hp-omen"
        
        tgp_path = f"{base}/gpu_tgp"
        ppab_path = f"{base}/gpu_ppab"

        if not sysfs_exists(tgp_path):
            return

        try:
            if profile == "performance":
                sysfs_write(tgp_path, "1")
                sysfs_write(ppab_path, "1")
                logger.info("Kernel GPU Power: TGP=Enabled, PPAB=Enabled")
            elif profile == "balanced":
                sysfs_write(tgp_path, "0")
                sysfs_write(ppab_path, "1")
                logger.info("Kernel GPU Power: TGP=Disabled, PPAB=Enabled")
            else: # power-saver / quiet / eco
                sysfs_write(tgp_path, "0")
                sysfs_write(ppab_path, "0")
                logger.info("Kernel GPU Power: TGP=Disabled, PPAB=Disabled")
        except Exception as e:
            logger.warning("Failed to sync Kernel GPU power: %s", e)


# ─── D-Bus Service ────────────────────────────────────────────────────────────


class PowerService:
    """
    <node>
      <interface name="com.yyl.hpmanager.power">
        <method name="SetPowerProfile"><arg type="s" name="profile" direction="in"/><arg type="s" name="resp" direction="out"/></method>
        <method name="GetPowerProfile"><arg type="s" name="j" direction="out"/></method>
        <method name="Ping"><arg type="s" name="resp" direction="out"/></method>
      </interface>
    </node>
    """

    def __init__(self):
        self._ctrl = PowerProfileController()
        self._config = ServiceConfig("power", {"power_profile": "balanced"})
        self._config.load()

        # Restore saved profile
        if self._ctrl.available:
            saved = self._config.get("power_profile", "balanced")
            if saved in self._ctrl.get_profiles():
                if self._ctrl.get_active() != saved:
                    ok = self._ctrl.set_profile(saved)
                    logger.info("Restored power profile '%s' (success=%s)", saved, ok)
                else:
                    logger.info("Power profile already '%s', skipping", saved)

    def SetPowerProfile(self, profile):
        if profile not in self._ctrl.get_profiles():
            return "FAIL"
        ok = self._ctrl.set_profile(profile)
        if ok:
            self._config.set("power_profile", profile)
            self._config.save()
        return "OK" if ok else "FAIL"

    def GetPowerProfile(self):
        return json.dumps(
            {
                "available": self._ctrl.available,
                "active": self._ctrl.get_active(),
                "profiles": self._ctrl.get_profiles(),
            }
        )

    def Ping(self):
        return "OK"


# ─── Entry point ──────────────────────────────────────────────────────────────


def main():
    service = PowerService()
    if service._ctrl.available:
        logger.info("Power profiles: %s", service._ctrl.get_profiles())
    run_service("com.yyl.hpmanager.power", service, service_name="power")


if __name__ == "__main__":
    main()
