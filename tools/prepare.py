#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare ROM-specific allowlists and policy without modifying the ROM checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from fetch_prebuilts import ROOT, verify_all

OSLO = ["com.google.oslo/com.google.oslo.OsloOverlay",
        "com.google.oslo/com.google.oslo.OsloSensorManager"]
DEBUG_PROPERTIES = ["pixel.oslo.airplane_mode.allowed_override", "pixel.oslo.allowed_override", "pixel.oslo.gating"]


def read_allowlist(paths):
    selected = None
    for path in paths:
        root = ET.parse(path).getroot()
        values = [n for n in root if n.get("name") == "config_pluginAllowlist"]
        if len(values) > 1:
            raise ValueError("Duplicate plugin allowlist in " + str(path))
        if values:
            selected = [(n.text or "").strip() for n in values[0]]
    if selected is None:
        raise ValueError("No config_pluginAllowlist found; select the ROM's active SystemUI resource")
    result = []
    for value in selected + OSLO:
        if value == "com.google.oslo":
            continue
        if not re.fullmatch(r"[A-Za-z_][\w.]*(?:/[A-Za-z_.][\w.$]*)?", value):
            raise ValueError("Unexpected plugin allowlist entry: " + value)
        if value not in result:
            result.append(value)
    return result


def prepare(rom_root, allowlists, policy_dirs, existing_policy=False, root=ROOT):
    verify_all(root)
    values = read_allowlist(allowlists)
    # Validate every input before writing generated files.
    policy_files = list(dict.fromkeys(p for d in policy_dirs for p in d.rglob("*.te")))
    policy_text = "\n".join(p.read_text() for p in policy_files)
    if not policy_dirs:
        raise ValueError("Provide --policy-dir for the active Floral device policy")
    for name in ["persist_oslo_file", "vendor_aware_available_prop"]:
        if not re.search(r"\b" + name + r"\b", policy_text):
            raise ValueError("Base Floral policy is missing " + name)
    for d in policy_dirs:
        for path in d.rglob("seapp_contexts"):
            for line in path.read_text().splitlines():
                fields = dict(p.split("=", 1) for p in line.split() if "=" in p)
                if (not line.lstrip().startswith("#") and fields.get("user") == "_app"
                        and fields.get("isPrivApp") == "true" and fields.get("seinfo") == "platform"
                        and fields.get("name") == "com.google.oslo" and not existing_policy):
                    raise ValueError("Existing equally specific Oslo label in " + str(path)
                                     + "; use --use-existing-oslo-policy or remove that older label")
    if existing_policy:
        if not re.search(r"type\s+oslo_app\s*,[^;]*\bcoredomain\b|typeattribute\s+oslo_app\s+coredomain", policy_text):
            raise ValueError("Existing Oslo policy must declare oslo_app as a platform coredomain")
    debug_type = "pixel_oslo_debug_prop" if re.search(r"\bpixel_oslo_debug_prop\b", policy_text) else "floral_oslo_debug_prop"
    xml = ET.Element("resources")
    array = ET.SubElement(xml, "string-array", name="config_pluginAllowlist", translatable="false")
    for value in values:
        ET.SubElement(array, "item").text = value
    ET.indent(xml, space="    ")
    generated = root / "generated"
    generated.mkdir(exist_ok=True)
    resources = root / "overlay/res/values/config.xml"
    resources.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(xml).write(resources, encoding="utf-8", xml_declaration=True)
    (generated / "policy.mk").write_text("FLORAL_MOTION_USE_EXISTING_OSLO_POLICY := " + str(existing_policy).lower() + "\n")
    if not existing_policy:
        for kind in ["public", "private"]:
            (generated / "sepolicy/system_ext" / kind).mkdir(parents=True, exist_ok=True)
        public = generated / "sepolicy/system_ext/public/property.te"
        private = generated / "sepolicy/system_ext/private/oslo_debug.te"
        contexts = generated / "sepolicy/system_ext/private/property_contexts"
        public.write_text("system_internal_prop(floral_oslo_debug_prop)\n" if debug_type == "floral_oslo_debug_prop" else "")
        private.write_text("get_prop(floral_oslo_app, " + debug_type + ")\n")
        contexts.write_text("\n".join(p + " u:object_r:floral_oslo_debug_prop:s0 exact string" for p in DEBUG_PROPERTIES) + "\n"
                            if debug_type == "floral_oslo_debug_prop" else "")
    for path in ["Android.bp", "settings/Android.bp"]:
        target = root / path
        target.write_text(target.with_suffix(".bp.in").read_text())
    output_paths = ["Android.bp", "settings/Android.bp", "overlay/res/values/config.xml", "generated/policy.mk"]
    inputs = list(dict.fromkeys(allowlists + policy_files))
    profile = {"allowlist": values, "use_existing_oslo_policy": existing_policy,
               "debug_property_type": debug_type,
               "input_files": [{"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs],
               "output_files": [{"path": p, "sha256": hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in output_paths]}
    (generated / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    print("Motion Sense plugin prepared; existing non-Oslo allowlist entries retained:", len(values) - 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom-root", type=Path, default=Path.cwd())
    parser.add_argument("--allowlist-xml", type=Path, action="append", default=[],
                        help="Active SystemUI overlays, lowest to highest priority")
    parser.add_argument("--policy-dir", type=Path, action="append", required=True)
    parser.add_argument("--use-existing-oslo-policy", action="store_true")
    args = parser.parse_args()
    try:
        rom = args.rom_root.resolve()
        def absolute(path): return path if path.is_absolute() else rom / path
        paths = [rom / "frameworks/base/packages/SystemUI/res/values/config.xml"]
        paths += [absolute(p) for p in args.allowlist_xml]
        dirs = [absolute(p) for p in args.policy_dir]
        for path in dirs:
            if not path.is_dir(): raise ValueError("Policy directory missing: " + str(path))
        prepare(rom, paths, dirs, args.use_existing_oslo_policy)
    except (OSError, ValueError, ET.ParseError) as error:
        print("Motion Sense setup:", error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
