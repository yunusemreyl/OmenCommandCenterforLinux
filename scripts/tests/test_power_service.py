import os
import sys
import types
import unittest
from unittest import mock


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src", "daemon"))

sys.modules.setdefault("pydbus", types.SimpleNamespace(SystemBus=lambda: None))

from services import power_service


class PowerServiceOmenDirectReadbackTest(unittest.TestCase):
    def make_controller(self):
        controller = power_service.PowerProfileController.__new__(power_service.PowerProfileController)
        controller.available = True
        controller.mode = "omen_direct"
        controller.proxy = None
        return controller

    def test_get_active_reads_thermal_profile(self):
        controller = self.make_controller()
        with mock.patch.object(power_service, "sysfs_exists", side_effect=lambda path: path.endswith("thermal_profile")), \
             mock.patch.object(power_service, "sysfs_read", return_value=1), \
             mock.patch.object(power_service, "sysfs_read_str", return_value="balanced"):
            self.assertEqual(controller.get_active(), "performance")

    def test_get_active_reads_platform_profile_string(self):
        controller = self.make_controller()
        with mock.patch.object(power_service, "sysfs_exists", side_effect=lambda path: path.endswith("platform_profile")), \
             mock.patch.object(power_service, "sysfs_read", return_value=0), \
             mock.patch.object(power_service, "sysfs_read_str", return_value="performance"):
            self.assertEqual(controller.get_active(), "performance")


class PowerServiceKernelGpuPowerSyncTest(unittest.TestCase):
    def make_controller(self):
        controller = power_service.PowerProfileController.__new__(power_service.PowerProfileController)
        controller.available = True
        controller.mode = "omen_direct"
        controller.proxy = None
        return controller

    def test_hp_omen_fallback_path(self):
        controller = self.make_controller()

        def exists_side_effect(path):
            return path in {
                "/sys/devices/platform/hp-omen/gpu_tgp",
                "/sys/devices/platform/hp-omen/gpu_ppab",
            }

        with mock.patch.object(power_service, "sysfs_exists", side_effect=exists_side_effect), \
             mock.patch.object(power_service, "sysfs_write", return_value=True) as write_mock:
            controller._sync_kernel_gpu_power("performance")

        write_mock.assert_has_calls(
            [
                mock.call("/sys/devices/platform/hp-omen/gpu_tgp", "1"),
                mock.call("/sys/devices/platform/hp-omen/gpu_ppab", "1"),
            ]
        )

    def test_warning_logged_on_write_failure(self):
        controller = self.make_controller()
        with mock.patch.object(power_service, "sysfs_exists", return_value=True), \
             mock.patch.object(power_service, "sysfs_write", side_effect=[True, False]), \
             mock.patch.object(power_service.logger, "warning") as warn_mock:
            controller._sync_kernel_gpu_power("balanced")

        warn_mock.assert_any_call("Failed to apply Kernel GPU power profile: %s", "balanced")


if __name__ == "__main__":
    unittest.main()
