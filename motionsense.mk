# SPDX-License-Identifier: Apache-2.0
# Product bootstrap can run before Android defines the my-dir helper.
FLORAL_MOTION_PLUGIN_PATH := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))

ifeq ($(wildcard $(FLORAL_MOTION_PLUGIN_PATH)/generated/profile.json),)
$(error Run $(FLORAL_MOTION_PLUGIN_PATH)/tools/fetch_prebuilts.py and tools/prepare.py before building)
endif
FLORAL_MOTION_READY := $(shell python3 "$(FLORAL_MOTION_PLUGIN_PATH)/tools/verify_ready.py" 2>&1)
ifneq ($(FLORAL_MOTION_READY),ready)
$(error $(FLORAL_MOTION_READY))
endif

PRODUCT_SOONG_NAMESPACES += $(FLORAL_MOTION_PLUGIN_PATH)
PRODUCT_VENDOR_PROPERTIES += ro.vendor.aware_available?=true
# Builders may opt in to the same country override used by the Floral port.
FLORAL_MOTION_COUNTRY_OVERRIDE ?= false
ifeq ($(FLORAL_MOTION_COUNTRY_OVERRIDE),true)
PRODUCT_PRODUCT_PROPERTIES += pixel.oslo.allowed_override=1
else ifneq ($(FLORAL_MOTION_COUNTRY_OVERRIDE),false)
$(error FLORAL_MOTION_COUNTRY_OVERRIDE must be true or false)
endif
# The plugin owns this allowlist, including on trees with the older device copy.
PRODUCT_COPY_FILES := $(filter-out %:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/permissions/privapp-permissions-floral-motionsense.xml,$(PRODUCT_COPY_FILES))
# Inherit this file AFTER the base device and vendor products.
PRODUCT_PACKAGES := $(filter-out OsloFeedback MotionSenseBridge MotionSenseBridgePrebuilt GoogleOsloSystemUIOverlay,$(PRODUCT_PACKAGES))
PRODUCT_PACKAGES += \
    FloralOsloFeedback \
    FloralMotionSenseBridge \
    FloralMotionSenseSettings \
    FloralMotionSensePrivappPermissions \
    FloralOsloSystemUIOverlay \
    FloralOsloFrameworkOverlay
