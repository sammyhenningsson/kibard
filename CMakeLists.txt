# This repo is itself the Zephyr module the build loads via ZMK_EXTRA_MODULES
# (see zephyr/module.yml): it supplies the kibard shield under boards/shields,
# the vendored layer-status sources under src/appcompanion and the Strata
# nice!view screen under src/strata.
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

# Strata nice!view status screen (vendored in src/strata, see its README).
# It provides zmk_display_status_screen(), as does ZMK's stock nice!view
# widget, so only one of them can be on.
if(CONFIG_NICE_VIEW_STRATA)
    if(CONFIG_NICE_VIEW_WIDGET_STATUS)
        message(FATAL_ERROR "CONFIG_NICE_VIEW_STRATA replaces the stock nice!view status screen; "
            "set CONFIG_NICE_VIEW_WIDGET_STATUS=n")
    endif()

    target_sources(app PRIVATE
        src/strata/assets.c
        src/strata/draw.c
        src/strata/screen.c
    )
endif()
