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


if __name__ == "__main__":
    unittest.main()
