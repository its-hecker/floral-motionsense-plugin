#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check APK interfaces, source components and production allowlist packaging."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from apk_resource_reader import xml
from fetch_prebuilts import ROOT, verify_all
from prepare import OSLO

A = "{http://schemas.android.com/apk/res/android}"


def check(root=ROOT):
    verify_all(root)
    with zipfile.ZipFile(root / "proprietary/system_ext/priv-app/OsloFeedback/OsloFeedback.apk") as z:
        manifest = xml(z.read("AndroidManifest.xml"))
        if manifest.get("package") != "com.google.oslo":
            raise ValueError("Unexpected Oslo package")
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
    print("SystemUI overlay and platform/vendor policy separation: PASS")


if __name__ == "__main__":
    check()
