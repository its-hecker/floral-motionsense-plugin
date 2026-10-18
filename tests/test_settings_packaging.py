# SPDX-License-Identifier: Apache-2.0
"""Prevent the privileged-permission boot failure and duplicate Settings launcher."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_port import check_settings_permissions


class SettingsPackagingTests(unittest.TestCase):
    def test_real_plugin_owns_the_exact_partition_grant(self):
        check_settings_permissions(ROOT)

    def test_changed_grants_partitions_and_launcher_entries_are_rejected(self):
        for filename, old, new in [
            ("configs/privapp-permissions-floral-motionsense.xml", "WRITE_SECURE_SETTINGS", "OTHER_PERMISSION"),
            ("configs/privapp-permissions-floral-motionsense.xml", "org.hecker.floral.motionsense", "wrong.package"),
            ("Android.bp.in", "sub_dir: \"permissions\"", "sub_dir: \"sysconfig\""),
            ("settings/Android.bp.in", 'required: ["FloralMotionSensePrivappPermissions"]', 'required: []'),
            ("settings/AndroidManifest.xml", "android.intent.category.DEFAULT", "android.intent.category.LAUNCHER"),
        ]:
            with self.subTest(filename=filename, change=old), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for path in ("configs/privapp-permissions-floral-motionsense.xml", "Android.bp.in",
                             "settings/Android.bp.in", "settings/AndroidManifest.xml"):
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / path, target)
                target = root / filename
                self.assertIn(old, target.read_text())
                target.write_text(target.read_text().replace(old, new))
                with self.assertRaises(ValueError):
                    check_settings_permissions(root)


if __name__ == "__main__":
    unittest.main()
