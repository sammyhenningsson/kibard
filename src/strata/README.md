# Strata nice!view screen (vendored)

The status screen on the Kibård v2 left half's nice!view: connection and link
status at the top, the five Bluetooth profiles under it, the active layer's
`display-name` in the middle and the battery at the bottom.

Vendored from [am/nice-view-strata](https://github.com/am/nice-view-strata)
at `e7f18e2097600fa5d8226dd572cb869d703bf487` (2026-11-19), MIT, see
[LICENSE](LICENSE). It is built as part of this repo's Zephyr module: the
`CONFIG_NICE_VIEW_STRATA` block in the root `CMakeLists.txt` and `Kconfig`.

## Local changes

- **LVGL 9.** Upstream supports ZMK v0.3 (LVGL 8) only; this repo tracks ZMK
  `main` for layer locking. `screen.c` now draws into an 8-bit grey (`L8`)
  canvas, the format ZMK's own nice!view widget uses on `main`, with the row
  stride from `lv_draw_buf_width_to_stride()`. Kconfig also selects
  `LV_USE_IMAGE`, which LVGL 9's canvas needs.
- **Layer name instead of the layer stack.** The tile stack and its
  `CONFIG_NICE_VIEW_STRATA_BASE_LAYER_SECOND` option are gone. `draw.c` writes
  the name from `zmk_keymap_layer_name()` in a 1-bit pixel font, centred, and
  breaks it onto more lines when it is wider than the screen: at spaces
  first, and inside a word only when the word alone is too wide, in pieces of
  about equal width. A layer without a `display-name` shows its number.
- **Edge margins.** The connection row and the battery sit 12 px (one
  battery height) in from the top and bottom of the screen, which are hard
  to see on the mounted panel.
- **The font** is `assets/font.txt`: Noto Sans ExtraCondensed Bold at 17 px
  (SIL Open Font License 1.1), rasterised without anti-aliasing by
  `tools/strata-gen-font.py`. At that size each word of every layer name in
  `config/kibard.keymap` fits on one line; `Graphmod` fills all 68 px. It
  covers printable ASCII plus `ÅÄÖåäöÉéÜü`; anything else draws as `?`.
- Upstream's `scripts/gen_assets.py` is `tools/strata-gen-assets.py` here, and
  also turns `font.txt` into C.
- `tools/strata-preview.sh` builds `draw.c` for the host and renders one screen
  per keymap layer to a PNG, to check a font or layout change without
  flashing.

The peripheral (right half) code is kept as upstream wrote it, but unused: the
v2 right half has no nice!view.

## Changing the font or icons

```sh
tools/strata-gen-font.py FONT.ttf SIZE   # only to start over from an outline font
$EDITOR src/strata/assets/font.txt       # or icons.txt; one character per pixel
tools/strata-gen-assets.py               # regenerates assets.c and assets_list.h
tools/strata-preview.sh                  # writes strata-preview.png
```

Commit `assets.c` and `assets_list.h` with the text sources; the firmware
build does not run Python.
