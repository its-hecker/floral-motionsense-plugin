#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check APK interfaces, source components and production allowlist packaging."""
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET
from apk_resource_reader import xml
from fetch_prebuilts import ROOT, verify_all
from prepare import OSLO

A = "{http://schemas.android.com/apk/res/android}"


def check_settings_permissions(root=ROOT):
    manifest = ET.parse(root / "settings/AndroidManifest.xml").getroot()
    grants = ET.parse(root / "configs/privapp-permissions-floral-motionsense.xml").getroot()
    entries = grants.findall("privapp-permissions")
    if (len(entries) != 1 or entries[0].get("package") != manifest.get("package")
            or [p.get("name") for p in entries[0].findall("permission")]
            != ["android.permission.WRITE_SECURE_SETTINGS"]):
        raise ValueError("Motion Sense needs exactly its own WRITE_SECURE_SETTINGS allowlist")
    bp = (root / "Android.bp.in").read_text()
    blocks = re.findall(r'(?ms)^prebuilt_etc\s*\{\s*name:\s*"FloralMotionSensePrivappPermissions",.*?^\}', bp)
    required = ['src: "configs/privapp-permissions-floral-motionsense.xml"',
                'filename: "privapp-permissions-floral-motionsense.xml"',
                'sub_dir: "permissions"', 'system_ext_specific: true']
    if len(blocks) != 1 or not all(value in blocks[0] for value in required):
        raise ValueError("Motion Sense privileged allowlist must install once on system_ext")
    settings = (root / "settings/Android.bp.in").read_text()
    if not all(value in settings for value in ['privileged: true', 'system_ext_specific: true',
                                              'required: ["FloralMotionSensePrivappPermissions"]']):
        raise ValueError("Motion Sense settings must require its matching privileged allowlist")
    names = {node.get(A + "name") for node in manifest.findall(".//action")}
    categories = {node.get(A + "name") for node in manifest.findall(".//category")}
    if "com.android.settings.action.IA_SETTINGS" not in names or "android.intent.category.LAUNCHER" in categories:
        raise ValueError("Motion Sense must provide its Settings entry without an app-drawer duplicate")


def check(root=ROOT):
    verify_all(root)
    check_settings_permissions(root)
    with zipfile.ZipFile(root / "proprietary/system_ext/priv-app/OsloFeedback/OsloFeedback.apk") as z:
        manifest = xml(z.read("AndroidManifest.xml"))
        if manifest.get("package") != "com.google.oslo":
            raise ValueError("Unexpected Oslo package")
        permissions = {p.get(A+"name") for p in manifest.findall("uses-permission")}
        if "android.permission.STATUS_BAR_SERVICE" not in permissions:
            raise ValueError("Motion feedback sender lacks its existing signature permission")
        dex = b''.join(z.read(name) for name in z.namelist()
                       if re.fullmatch(r'classes[0-9]*\.dex', name))
        for required in (b'Lcom/google/oslo/MotionFeedback;',
                         b'Lcom/google/oslo/MotionFeedback$Snapshot;',
                         b'com.google.oslo.HECKER_MOTION_FEEDBACK'):
            if required not in dex:
                raise ValueError("Coral feedback bridge missing from the pinned APK")
        services = {s.get(A+"name"): s for s in manifest.findall("application/service")}
        for name, action in [("com.google.oslo.OsloOverlay", "com.android.systemui.action.PLUGIN_OVERLAY"),
                             ("com.google.oslo.OsloSensorManager", "com.android.systemui.action.PLUGIN_SENSOR_MANAGER")]:
            if name not in services or action not in {n.get(A+"name") for n in services[name].findall("intent-filter/action")}:
                raise ValueError("Required SystemUI plugin interface missing: " + name)
    with zipfile.ZipFile(root / "proprietary/product/app/MotionSenseBridge/MotionSenseBridge.apk") as z:
        if "classes.dex" not in z.namelist():
            raise ValueError("Motion Sense bridge is a nonfunctional factory stub")
    settings = ET.parse(root / "settings/AndroidManifest.xml").getroot()
    package = settings.get("package")
    if package != "org.hecker.floral.motionsense" or settings.get(A+"sharedUserId") != "android.uid.system":
        raise ValueError("Standalone settings package/identity incorrect")
    for component in settings.find("application"):
        if component.tag not in ["activity", "service"]:
            continue
        name = component.get(A+"name")
        if name.startswith("."): name = package + name
        path = root / "settings/src" / (name.replace(".", "/") + ".java")
        if not path.is_file():
            raise ValueError("Manifest component has no source: " + name)
    if (root / "overlay/res/values/config.xml").exists():
        values = [n.text for n in ET.parse(root / "overlay/res/values/config.xml").getroot().find("string-array")]
        if not set(OSLO) <= set(values):
            raise ValueError("Production Oslo allowlist components missing")
    policy = (root / "sepolicy/system_ext/public/floral_oslo_app.te").read_text()
    if "type floral_oslo_app, domain, coredomain;" not in policy:
        raise ValueError("Oslo must be a platform coredomain")
    print("Oslo APK interfaces, full bridge implementation and standalone settings components: PASS")
    print("SystemUI overlay, Settings entry/privileged allowlist and platform/vendor policy separation: PASS")


if __name__ == "__main__":
    check()
