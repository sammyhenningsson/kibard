# This repo is itself the Zephyr module the build loads via ZMK_EXTRA_MODULES
# (see zephyr/module.yml): it supplies the kibard shield under boards/shields
# and the vendored layer-status sources under src/appcompanion.
#
# ZMK exports only `app/module/include` to Zephyr modules; core headers such as
# <zmk/hid.h>, <zmk/endpoints.h> and <zmk/keymap.h> live in the app's own
# `app/include`, which modules don't get. The layer-status sources below build
# as a standalone zephyr_library() and include those headers, so they fail to
# compile without this. Adding the directory to the global Zephyr interface
# makes it visible to every module in the build.
#
# Drop this once ZMK exports those headers to modules (or these sources switch
# to target_sources(app ...) the way zmk-adaptive-key does).
zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)

if(CONFIG_ZMK_LAYER_STATUS_USB_HID OR CONFIG_ZMK_LAYER_STATUS_BLE_HID)
    zephyr_library()
    zephyr_include_directories(src/appcompanion)
endif()

if(CONFIG_ZMK_LAYER_STATUS_USB_HID)
    zephyr_library_sources(src/appcompanion/layer_status_usb_hid.c)
endif()

if(CONFIG_ZMK_LAYER_STATUS_BLE_HID)
    zephyr_library_sources(src/appcompanion/layer_status_ble_hid.c)
endif()
