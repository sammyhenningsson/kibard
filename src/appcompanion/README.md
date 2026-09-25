# Layer status (vendored)

Firmware side of the [Keyboard Layers App
Companion](https://github.com/maatthc/keyboard_layers_app_companion): it
watches `zmk_layer_state_changed` and reports the highest active layer to the
host. The host-side files live in [`companion/`](../../companion).

Vendored from
[maatthc/zmk-feature-appcompanion](https://github.com/maatthc/zmk-feature-appcompanion)
@ `e66cbb6` (2026-01-24, MIT — see `LICENSE`), with one change: ZMK renamed
`zmk_endpoints_send_report` to `zmk_endpoint_send_report` after v0.3, so
`layer_status_ble_hid.c` calls the singular name. Upstream still calls the old
one and no longer builds against ZMK `main`, which is what `config/west.yml`
tracks — hence the copy instead of a west project.

The build wiring is at the repo root: `CMakeLists.txt` compiles whichever of
the two variants is enabled, `Kconfig` sources this directory's `Kconfig`, and
`zephyr/module.yml` points Zephyr at both. `config/kibard_left.conf` picks the
variant (BLE/HID on, USB raw-HID off).

## Keeping it in sync

Upstream is quiet (last commit Jan 2026). To pull in a newer version, diff this
directory against upstream's `src/`, `include/` and `Kconfig`, and re-apply the
rename if it is still missing there.
