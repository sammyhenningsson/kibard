# ZMK v0.3 exports only `app/module/include` to Zephyr modules; core headers
# such as <zmk/hid.h>, <zmk/endpoints.h> and <zmk/keymap.h> live in the app's
# own `app/include`, which modules don't get. The zmk-feature-appcompanion
# module builds as a standalone zephyr_library() and includes those headers, so
# it fails to compile without this. Adding the directory to the global Zephyr
# interface makes it visible to every module in the build.
#
# Drop this once ZMK exports those headers to modules (or the module switches
# to target_sources(app ...) the way zmk-adaptive-key does).
zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
