# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

ZMK firmware configuration for **Kibård**, a custom split keyboard. The firmware runs on `nice_nano_v2` controllers (nRF52840 BLE) on both halves.

## Building firmware

Firmware is built via GitHub Actions — push to the repo and download the `.uf2` artifacts from the Actions run. The build matrix is defined in `build.yaml` and produces two artifacts: `kibard_left` and `kibard_right`.

There is no local build command in this repo. Local ZMK builds require a separate Zephyr/West development environment (see [ZMK docs](https://zmk.dev/docs/development/setup)).

## Architecture

### Hardware layout

Split keyboard, 5 columns × 4 rows per half, `col2row` diode direction. The matrix transform is 10 columns × 4 rows with 4 thumb keys:

```
Left half (col 0–4)    Right half (col 5–9)
[ 0  1  2  3  4]       [ 5  6  7  8  9]   row 0
[10 11 12 13 14]       [15 16 17 18 19]   row 1
[20 21 22 23 24]       [25 26 27 28 29]   row 2
         [30 31]       [32 33]            thumbs (row 3)
```

Left half = BLE central + USB host. Right half = BLE peripheral only.

### Key files

| File | Purpose |
|------|---------|
| `boards/shields/kibard/kibard.dtsi` | Shared matrix transform and kscan skeleton |
| `boards/shields/kibard/kibard_left.overlay` | Left half GPIO pin assignments |
| `boards/shields/kibard/kibard_right.overlay` | Right half GPIO pin assignments (col-offset = 5) |
| `config/kibard.keymap` | All layers, behaviors, macros, combos |
| `config/kibard_left.conf` | Left: split central + BLE |
| `config/kibard_right.conf` | Right: split peripheral + BLE + USB |
| `config/west.yml` | ZMK version pin (v0.3) |
| `build.yaml` | GitHub Actions build matrix |
| `companion/` | Layer-display host files (`config.ini` + rendered layer images) — see `companion/README.md` |
| `tools/render-layer-images.sh` | Regenerates `companion/images/` from the keymap via keymap-drawer |
| `companion/install.sh` | Symlinks `companion/` into a Keyboard Layers App Companion checkout |

### Keymap layers

Defined in `config/kibard.keymap`. Layer indices:

| # | Name | Activation |
|---|------|-----------|
| 0 | Graphmod (default) | base layer |
| 1 | Symbols | left thumb hold (SPACE, pos 30) |
| 2 | Numpad | left thumb hold (ESC, pos 31) |
| 3 | Right | right thumb hold (RET, pos 33) |
| 4 | Navigate | right thumb hold (TAB, pos 32) |
| 5 | Vim | `lt L_VIM V` (pos 14) |
| 6 | Mouse | `to L_MOUSE` from Navigate |
| 7 | Functions | `to L_FUNC` from Navigate |
| 8 | B (Bluetooth/system) | `to L_B` from Navigate |

`L_MAIN` always equals `L_GRAPHMOD` (layer 0). The triple-combo `30+31+32` returns to main (`&to L_MAIN`) — this is the only combo defined.

### Home row mods

`HML` (left hand) and `HMR` (right hand) are `zmk,behavior-hold-tap` with `flavor = "balanced"`, `tapping-term-ms = 250`, `quick-tap-ms = 175`, `require-prior-idle-ms = 150`, `hold-trigger-on-release`, and positional `hold-trigger-key-positions` restricting each to the opposite hand. Home row mod order, index→pinky (inner to outer): Alt / Ctrl / Shift.

### Swedish key defines

All `SE_*` macros at the top of `kibard.keymap` map Swedish characters and symbols to their positions on a Swedish keyboard layout (e.g. `SE_AA`, `SE_ADIA`, `SE_OO` for å, ä, ö). On the base layer å/ä/ö sit directly on keys (`SE_AA` at pos 9, `SE_ADIA` at pos 27, `SE_OO` at pos 28).

### Vim macros

The Vim layer provides keyboard macros for `:w`, `:w!`, `:q`, `:q!`, `:qa`, `:Gwrite`, and `Ctrl+W` window navigation (h/j/k/l).
