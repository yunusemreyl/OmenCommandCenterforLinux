#!/usr/bin/env python3
"""OMEN Command Center for Linux — MUX (GPU Switch) Microservice."""

import json, os, shutil, subprocess, sys, threading, time, typing

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.logging_config import setup_logging
from common.config import ServiceConfig
from common.sysfs import sysfs_read, sysfs_write, sysfs_exists
from common.dbus_helpers import run_service, system_sleeping

logger = setup_logging("mux")

VALID_GPU_MODES = {"hybrid", "discrete", "integrated"}


class MUXController:
    def __init__(self):
        self.envycontrol = shutil.which("envycontrol")
        self.supergfxctl = shutil.which("supergfxctl")
        self.prime_select = shutil.which("prime-select")
        self.backend: typing.Optional[str] = None
        self._cached_mode = "unknown"
        self._last_check = 0.0

    def detect_backend(self, forced="auto"):
        available = self.get_available_backends()
        if forced != "auto" and forced in available:
            self.backend = forced
            logger.info("MUX backend: %s (forced)", self.backend)
            return
        if "envycontrol" in available:
            self.backend = "envycontrol"
        elif "supergfxctl" in available:
            self.backend = "supergfxctl"
        elif "prime-select" in available:
            self.backend = "prime-select"
        else:
            self.backend = None
        logger.info("MUX backend: %s (auto)", self.backend or "none")

    def get_available_backends(self):
        b = []
        if self.envycontrol: b.append("envycontrol")
        if self.supergfxctl: b.append("supergfxctl")
        if self.prime_select: b.append("prime-select")
        return b

    def set_backend(self, backend):
        if backend in self.get_available_backends():
            self.backend = backend
            self._cached_mode = "unknown"
            self._last_check = 0.0
            logger.info("MUX backend switched to: %s", backend)
            return True
        return False

    def is_available(self):
        return self.backend is not None

    def get_backend(self):
        return self.backend or "none"

    @staticmethod
    def _normalize_mode(raw_mode):
        mode = str(raw_mode or "").strip().lower()
        if "hybrid" in mode or "on-demand" in mode:
            return "hybrid"
        if "integrated" in mode or "intel" in mode or "igpu" in mode:
            return "integrated"
        if "discrete" in mode or "dedicated" in mode or "nvidia" in mode or "dgpu" in mode:
            return "discrete"
        return "unknown"

    def get_mode(self):
        now = time.time()
        if now - self._last_check < 10.0:
            return self._cached_mode
        mode = "unknown"
        try:
            if self.backend == "envycontrol" and self.envycontrol:
                mode = subprocess.check_output([self.envycontrol, "--query"], stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
            elif self.backend == "supergfxctl" and self.supergfxctl:
                mode = subprocess.check_output([self.supergfxctl, "-g"], stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
            elif self.backend == "prime-select" and self.prime_select:
                mode = subprocess.check_output([self.prime_select, "query"], stderr=subprocess.STDOUT, timeout=5).decode().strip().lower()
        except Exception as e:
            logger.debug("MUX get_mode error: %s", e)
        self._cached_mode = self._normalize_mode(mode)
        self._last_check = now
        return self._cached_mode

    def set_mode(self, mode):
        try:
            if self.backend == "envycontrol" and self.envycontrol:
                m = {"hybrid":"hybrid","discrete":"nvidia","integrated":"integrated"}.get(mode,mode)
                subprocess.run([self.envycontrol, "-s", m], check=True, timeout=10)
            elif self.backend == "supergfxctl" and self.supergfxctl:
                m = {"hybrid":"Hybrid","discrete":"Dedicated","integrated":"Integrated"}.get(mode,mode)
                subprocess.run([self.supergfxctl, "-m", m], check=True, timeout=10)
            elif self.backend == "prime-select" and self.prime_select:
                m = {"hybrid":"on-demand","discrete":"nvidia","integrated":"intel"}.get(mode,mode)
                subprocess.run([self.prime_select, m], check=True, timeout=10)
            else:
                return "No backend"
            self._cached_mode = mode
            self._last_check = time.time()
            return "OK"
        except Exception as e:
            return f"Error: {e}"


class MUXService:
    """
    <node>
      <interface name="com.yyl.hpmanager.mux">
        <method name="SetGpuMode"><arg type="s" name="mode" direction="in"/><arg type="s" name="result" direction="out"/></method>
        <method name="GetGpuInfo"><arg type="s" name="j" direction="out"/></method>
        <method name="SetMuxBackend"><arg type="s" name="backend" direction="in"/><arg type="s" name="result" direction="out"/></method>
        <method name="Ping"><arg type="s" name="resp" direction="out"/></method>
      </interface>
    </node>
    """
    def __init__(self):
        self._mux = MUXController()
        self._config = ServiceConfig("mux", {"mux_backend": "auto"})
        self._config.load()
        self._mux.detect_backend(self._config.get("mux_backend", "auto"))
        self._cache_lock = threading.Lock()
        self._gpu_cache = {
            "available": self._mux.is_available(),
            "backend": self._mux.get_backend(),
            "available_backends": self._mux.get_available_backends(),
            "forced_backend": self._config.get("mux_backend", "auto"),
            "mode": "unknown",
        }
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while True:
            if system_sleeping.is_set():
                time.sleep(0.5); continue
            snap = {
                "available": self._mux.is_available(),
                "backend": self._mux.get_backend(),
                "available_backends": self._mux.get_available_backends(),
                "forced_backend": self._config.get("mux_backend", "auto"),
                "mode": self._mux.get_mode(),
            }
            with self._cache_lock:
                self._gpu_cache = snap
            time.sleep(30.0)

    def SetGpuMode(self, mode):
        if mode not in VALID_GPU_MODES: return "FAIL"
        result = self._mux.set_mode(mode)
        if result in ("OK", "OK_REBOOT_REQUIRED"):
            with self._cache_lock: self._gpu_cache["mode"] = mode
        return result

    def GetGpuInfo(self):
        with self._cache_lock: data = dict(self._gpu_cache)
        data["forced_backend"] = self._config.get("mux_backend", "auto")
        return json.dumps(data)

    def SetMuxBackend(self, backend):
        logger.info("SetMuxBackend: %s", backend)
        if backend == "auto":
            self._config.set("mux_backend", "auto"); self._config.save()
            self._mux.detect_backend("auto")
            with self._cache_lock:
                self._gpu_cache["backend"] = self._mux.get_backend()
                self._gpu_cache["forced_backend"] = "auto"
            return "OK"
        if self._mux.set_backend(backend):
            self._config.set("mux_backend", backend); self._config.save()
            with self._cache_lock:
                self._gpu_cache["backend"] = backend
                self._gpu_cache["forced_backend"] = backend
                self._gpu_cache["mode"] = "unknown"
            return "OK"
        return "FAIL"

    def Ping(self):
        return "OK"


def main():
    svc = MUXService()
    if svc._mux.is_available():
        logger.info("MUX backend: %s", svc._mux.get_backend())
    run_service("com.yyl.hpmanager.mux", svc, service_name="mux")

if __name__ == "__main__":
    main()
