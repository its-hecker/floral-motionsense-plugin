# Floral Motion Sense plugin — Android 17

Reusable Motion Sense build integration for **Pixel 4 (`flame`) and Pixel 4 XL
(`coral`)**, based on my working Android 17 port. This is a ROM source
plugin: builders inherit its product and board files, prepare their SystemUI
configuration, and build it into the ROM.

The package includes the patched OsloFeedback app, full Motion Sense bridge,
standalone settings app, stock-style animations, Air DJ controls, media-app
selection, glow controls, Glow Theme Studio and gesture training. A separate
platform-signed SystemUI overlay permits the two Oslo plugins on production
`user` builds. The settings app uses its own package,
`org.hecker.floral.motionsense`, so existing GoogleParts can remain installed.
Face ID is independently available from
[floral-3D-faceid-plugin](https://github.com/its-hecker/floral-3D-faceid-plugin).

## Prerequisites

- An Android 17 ROM with a working **Floral device/vendor/kernel base**. Keep
  the stock CHRE/Soli sensor stack, Oslo nanoapp, radar firmware and the phone's
  own `/mnt/vendor/persist/oslo` calibration.
- Standard AOSP SystemUI `OverlayPlugin` and `SensorManagerPlugin` support,
  `config_pluginAllowlist`, and the normal SystemUI plugin permission checks.
- AOSP SettingsLib, AndroidX Preference and the `lottie` Soong module. The small
  shared settings resource library is included; no Lineage SDK is required.
- The base device policy must provide `persist_oslo_file` and
  `vendor_aware_available_prop`. Include the actual selected policy directories
  when running setup.
- Platform signing keys and `system_ext` support, normally present in an
  Android 17 source build.

The binary inputs are downloaded once from immutable source commits and checked
against `prebuilts.lock.json`. The build itself performs no network downloads.
Use `tools/fetch_prebuilts.py --source OWNER/REPO=/path/to/checkout` for an
existing local copy, or `--verify-only` to check the cache.

## Integration

Run from the ROM source root:

```bash
git clone https://github.com/its-hecker/floral-motionsense-plugin \
  vendor/hecker/floral/motionsense
python3 vendor/hecker/floral/motionsense/tools/fetch_prebuilts.py
```

Prepare the overlay from your ROM's **active** SystemUI allowlist. The base
SystemUI resource is read automatically. Supply any selected overlays in
**lowest to highest priority** order; the last array replaces earlier arrays,
then the two Oslo components are appended. This preserves that ROM's plugin
configuration instead of copying Infinity's clock-plugin list.

For the common Coral device tree:

```bash
python3 vendor/hecker/floral/motionsense/tools/prepare.py \
  --policy-dir device/google/coral/sepolicy \
  --allowlist-xml device/google/coral/overlay-oslo/frameworks/base/packages/SystemUI/res/values/config.xml
```

Adjust those paths to your tree. If there are no SystemUI overlays, omit
`--allowlist-xml`. Include additional active policy roots with repeated
`--policy-dir` options. Do not supply another device's overlays or policy.

If the existing port already has a working, platform `oslo_app` policy, add
`--use-existing-oslo-policy`. Otherwise the plugin installs its own scoped
`floral_oslo_app` domain. Setup refuses an equally specific competing Oslo label
instead of creating conflicting `seapp_contexts` entries. Existing debug-property
types are reused; missing ones are generated inside this plugin.

After the base device and vendor product inheritance, add to `device.mk`:

```make
$(call inherit-product, vendor/hecker/floral/motionsense/motionsense.mk)
```

Add to `BoardConfig.mk`:

```make
include vendor/hecker/floral/motionsense/BoardConfigMotionSense.mk
```

The product removes the older `OsloFeedback`, bridge and
`GoogleOsloSystemUIOverlay` package selections and adds the plugin equivalents.
Keep this inheritance **after** the base/vendor products. If GoogleParts already
has a Motion Sense page, remove that older tile or use its page instead of
adding two entries to Settings. The standalone app also has a launcher entry
for ROMs without Settings tile discovery.

Build using your ROM's normal lunch target and build command. No Infinity-specific
lunch name is required. Rerun preparation after changing or syncing its selected
configuration. A read-only product check rejects changed binary/configuration
inputs before the build continues.

An optional local manifest:

```xml
<manifest>
    <remote name="hecker" fetch="https://github.com/its-hecker/" />
    <project name="floral-motionsense-plugin"
             path="vendor/hecker/floral/motionsense"
             remote="hecker" revision="main" />
</manifest>
```

## Verify the ROM and phone

Before flashing, confirm these APKs are included in the product output:

```bash
find out/target/product/coral/system_ext -name 'FloralOslo*.apk' -o -name 'FloralMotionSenseSettings.apk'
```

Use `flame` in the output path for Pixel 4. After flashing:

```bash
adb shell getprop ro.vendor.aware_available
adb shell settings get global aware_allowed
adb shell settings get secure aware_enabled
adb shell cmd overlay list --user 0 com.android.systemui
adb shell am start -n org.hecker.floral.motionsense/.motionsense.MotionSenseActivity
```

Test music skip/pause, silence, reach/wake, glow preview, music glow and the
training room. Test Air DJ and custom glow modes separately. If only settings
appear, capture SystemUI **startup** and verify both plugin components load:

```bash
adb logcat -b all -d > floral-motionsense-logcat.txt
adb shell dumpsys package com.google.oslo > floral-oslo-package.txt
adb shell dumpsys activity service com.android.systemui/.SystemUIService > floral-systemui.txt
```

`Plugin cannot be loaded in production` indicates allowlist/overlay access;
plugin version errors indicate a SystemUI interface mismatch. Availability is
still controlled by the real sensor stack and Oslo's availability settings.
Airplane mode, battery saver and user choices retain their normal behavior.

## Validation status

| Item | Status |
| --- | --- |
| Source port on Coral / Infinity Android 17 | Motion Sense gestures and glow confirmed on the phone |
| Standalone packaging | APK interfaces, checksums, setup tests and Motion Lab source/DEX checks in CI |
| Full ROM using these new package names | Requires builder validation |
| Flame and other Android 17 ROM forks | Integration targets; phone verification still required |

Custom Sidekick wallpapers are not included. The bridge supports compatible
clients; installing Google live wallpapers is a separate choice. The Face ID
plugin is optional and does not need this plugin to function.

## Sources and credits

Port, polish and additional features: **Hecker** (https://github.com/its-hecker). Google supplies the Oslo stack
and original Pixel assets; AOSP/LineageOS supply the platform APIs and settings
resources. Source provenance and immutable binary fingerprints are recorded in
`NOTICE` and `prebuilts.lock.json`.

The build integration follows the product/board-file pattern used by standalone
ROM features such as [ProtonAOSP ElmyraService](https://github.com/ProtonAOSP/android_packages_apps_ElmyraService)
and [Lunaris Dolby](https://github.com/tranQuila-Project/vendor_lunaris_dolby).
