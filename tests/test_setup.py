#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fetch_prebuilts as fetch
import prepare


class SetupTests(unittest.TestCase):
    def test_active_overlay_replaces_base_and_keeps_unrelated_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.xml"; overlay = root / "overlay.xml"
            base.write_text('<resources><string-array name="config_pluginAllowlist"><item>com.example.old</item></string-array></resources>')
            overlay.write_text('<resources><string-array name="config_pluginAllowlist"><item>com.example.current</item><item>com.google.oslo</item></string-array></resources>')
            self.assertEqual(prepare.read_allowlist([base, overlay]), ["com.example.current"] + prepare.OSLO)

    def test_unresolved_resource_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            path.write_text('<resources><string-array name="config_pluginAllowlist"><item>@string/plugin_name</item></string-array></resources>')
            with self.assertRaises(ValueError): prepare.read_allowlist([path])

    def test_checksum_mismatch_never_replaces_existing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); offline = root / "source"; offline.mkdir()
            (offline / "input.bin").write_bytes(b"wrong")
            target = root / "proprietary/input.bin"; target.parent.mkdir(); target.write_bytes(b"old")
            item = dict(repository="owner/repo", revision="a"*40, path="input.bin", destination="proprietary/input.bin",
                        sha256=hashlib.sha256(b"right").hexdigest(), size=5)
            (root / "prebuilts.lock.json").write_text(json.dumps({"schema":1,"artifacts":[item]}))
            with self.assertRaises(ValueError): fetch.fetch(root, {"owner/repo":offline})
            self.assertEqual(target.read_bytes(), b"old")
            self.assertFalse(list(target.parent.glob(".download-*")))

    def test_destination_cannot_escape_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root / "prebuilts.lock.json").write_text(json.dumps({"schema":1,"artifacts":[dict(destination="../outside",revision="a"*40,sha256="b"*64)]}))
            with self.assertRaises(ValueError): fetch.entries(root)


if __name__ == "__main__": unittest.main()
