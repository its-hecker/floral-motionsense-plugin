# SPDX-License-Identifier: Apache-2.0
FLORAL_MOTION_PLUGIN_PATH := $(call my-dir)

ifeq ($(wildcard $(FLORAL_MOTION_PLUGIN_PATH)/generated/profile.json),)
$(error Run $(FLORAL_MOTION_PLUGIN_PATH)/tools/fetch_prebuilts.py and tools/prepare.py before building)
endif
FLORAL_MOTION_READY := $(shell python3 "$(FLORAL_MOTION_PLUGIN_PATH)/tools/verify_ready.py" 2>&1)
ifneq ($(FLORAL_MOTION_READY),ready)
$(error $(FLORAL_MOTION_READY))
endif

PRODUCT_SOONG_NAMESPACES += $(FLORAL_MOTION_PLUGIN_PATH)
PRODUCT_VENDOR_PROPERTIES += ro.vendor.aware_available?=true
# Inherit this file AFTER the base device and vendor products.
PRODUCT_PACKAGES := $(filter-out OsloFeedback MotionSenseBridge MotionSenseBridgePrebuilt GoogleOsloSystemUIOverlay,$(PRODUCT_PACKAGES))
PRODUCT_PACKAGES += \
    FloralOsloFeedback \
    FloralMotionSenseBridge \
    FloralMotionSenseSettings \
    FloralOsloSystemUIOverlay \
    FloralOsloFrameworkOverlay
