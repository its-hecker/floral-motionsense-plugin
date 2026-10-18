# SPDX-License-Identifier: Apache-2.0
"""Parse the real product/board entry points before Android defines my-dir."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FACE = (ROOT / "faceid.mk").is_file()
PRODUCT = "faceid.mk" if FACE else "motionsense.mk"
BOARD = "BoardConfigFaceID.mk" if FACE else "BoardConfigMotionSense.mk"
VARIABLE = "FLORAL_FACEID_PLUGIN_PATH" if FACE else "FLORAL_MOTION_PLUGIN_PATH"
NAME = "faceid" if FACE else "motionsense"
PACKAGE = "FloralFaceIDHal" if FACE else "FloralOsloFeedback"


class ProductMakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.rom = Path(self.temporary.name)
        self.relative = Path("vendor/hecker/floral") / NAME
        self.plugin = self.rom / self.relative
        self.plugin.mkdir(parents=True)
        for entry in [PRODUCT, BOARD]:
            shutil.copyfile(ROOT / entry, self.plugin / entry)
        (self.plugin / "generated").mkdir()
        (self.plugin / "generated/profile.json").write_text("{}\n")
        (self.plugin / "generated/profile.mk").write_text("FLORAL_FACEID_ADD_VINTF := true\n")
        (self.plugin / "generated/policy.mk").write_text(
            "FLORAL_MOTION_USE_EXISTING_OSLO_POLICY := false\n")
        (self.plugin / "tools").mkdir()
        # Isolate the Make integration boundary; immutable input checks have their own tests.
        (self.plugin / "tools/verify_ready.py").write_text(
            "import os\nprint(os.environ.get('FLORAL_MAKE_TEST_READY', 'ready'))\n")

    def parse(self, entries=None, helper=False, stale=False, relative=None, country_override=None):
        relative = self.relative if relative is None else relative
        lines = ["TARGET_COPY_OUT_VENDOR := vendor",
                 "TARGET_COPY_OUT_SYSTEM_EXT := system_ext",
                 "PRODUCT_PACKAGES := KeepMe android.hardware.biometrics.face@1.0-service.google OsloFeedback",
                 "PRODUCT_COPY_FILES := keep:vendor/etc/keep legacy.xml:system_ext/etc/permissions/privapp-permissions-floral-motionsense.xml"]
        if country_override is not None:
            lines.append("FLORAL_MOTION_COUNTRY_OVERRIDE := " + country_override)
        if helper:
            lines.append("my-dir = $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))")
        for entry in [PRODUCT, BOARD] if entries is None else entries:
            lines.append("include " + str(relative / entry))
        lines.extend([
            "$(info PROBE_PATH=$(" + VARIABLE + "))",
            "$(info PROBE_NAMESPACES=$(PRODUCT_SOONG_NAMESPACES))",
            "$(info PROBE_PACKAGES=$(PRODUCT_PACKAGES))",
            "$(info PROBE_COPIES=$(PRODUCT_COPY_FILES))",
            "$(info PROBE_PROPERTIES=$(PRODUCT_PRODUCT_PROPERTIES))",
            "$(info PROBE_POLICY=$(BOARD_VENDOR_SEPOLICY_DIRS))",
            ".PHONY: all", "all:", "\t@:",
        ])
        environment = os.environ.copy()
        if stale:
            environment["FLORAL_MAKE_TEST_READY"] = "stale prepared inputs"
        return subprocess.run(["make", "--no-print-directory", "-f", "-"],
                              cwd=self.rom, env=environment, input="\n".join(lines) + "\n",
                              text=True, capture_output=True)

    def assert_valid(self, result, relative=None):
        relative = self.relative if relative is None else relative
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROBE_PATH=" + str(relative), result.stdout)
        self.assertIn("PROBE_NAMESPACES=" + str(relative), result.stdout)
        self.assertIn(PACKAGE, result.stdout)
        self.assertIn("KeepMe", result.stdout)
        self.assertIn("keep:vendor/etc/keep", result.stdout)
        self.assertIn(str(relative / "sepolicy/vendor"), result.stdout)

    def test_product_and_board_without_android_helper(self):
        self.assert_valid(self.parse())

    def test_product_and_board_with_android_helper(self):
        self.assert_valid(self.parse(helper=True))

    def test_board_entry_without_android_helper(self):
        result = self.parse(entries=[BOARD])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PROBE_PATH=" + str(self.relative), result.stdout)
        self.assertIn(str(self.relative / "sepolicy/vendor"), result.stdout)

    def test_missing_profile_is_still_rejected(self):
        (self.plugin / "generated/profile.json").unlink()
        result = self.parse()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.relative / "tools/"), result.stderr)

    def test_stale_profile_is_still_rejected(self):
        result = self.parse(stale=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale prepared inputs", result.stderr)

    def test_relocated_plugin_path(self):
        relative = Path("vendor/port-test/relocated")
        shutil.copytree(self.plugin, self.rom / relative)
        self.assert_valid(self.parse(relative=relative), relative)

    def test_plugin_owns_permission_module_and_removes_the_older_device_copy(self):
        result = self.parse()
        self.assert_valid(result)
        self.assertIn("FloralMotionSensePrivappPermissions", result.stdout)
        self.assertNotIn("legacy.xml:", result.stdout)

    def test_country_override_is_opt_in(self):
        self.assertNotIn("pixel.oslo.allowed_override", self.parse().stdout)
        result = self.parse(country_override="true")
        self.assert_valid(result)
        self.assertIn("PROBE_PROPERTIES=pixel.oslo.allowed_override=1", result.stdout)
        self.assertNotIn("airplane_mode.allowed_override", result.stdout)
        invalid = self.parse(country_override="yes")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("must be true or false", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
