# SPDX-License-Identifier: Apache-2.0
FLORAL_MOTION_PLUGIN_PATH := $(call my-dir)
include $(FLORAL_MOTION_PLUGIN_PATH)/generated/policy.mk

ifneq ($(FLORAL_MOTION_USE_EXISTING_OSLO_POLICY),true)
SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += \
    $(FLORAL_MOTION_PLUGIN_PATH)/sepolicy/system_ext/public \
    $(FLORAL_MOTION_PLUGIN_PATH)/generated/sepolicy/system_ext/public
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += \
    $(FLORAL_MOTION_PLUGIN_PATH)/sepolicy/system_ext/private \
    $(FLORAL_MOTION_PLUGIN_PATH)/generated/sepolicy/system_ext/private
BOARD_VENDOR_SEPOLICY_DIRS += $(FLORAL_MOTION_PLUGIN_PATH)/sepolicy/vendor
endif
