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
| `config/west.yml` | ZMK revision pin (`main` — see Layer lock) |
| `build.yaml` | GitHub Actions build matrix |
| `companion/` | Layer-display host files (`config.ini` + rendered layer images) — see `companion/README.md` |
| `tools/render-layer-images.sh` | Regenerates `companion/images/` from the keymap via keymap-drawer |
| `tools/sync-oryx.py` | Diffs the upstream ZSA Voyager layout in Oryx against this keymap — see below |
| `tools/oryx-snapshot.json` | Last-synced Oryx revision; the baseline `sync-oryx.py` diffs against |
| `companion/install.sh` | Symlinks `companion/` into a Keyboard Layers App Companion checkout |

### Keymap layers

Defined in `config/kibard.keymap`. Layer indices:

| # | Name | Activation |
|---|------|-----------|
| 0 | Graphmod (default) | base layer |
| 1 | Symbols | left thumb hold (`LT_TH L_SYM SPACE`, pos 30) |
| 2 | Symbols+ | `LT_TH L_SYMP SE_AT` hold on Symbols (pos 10) |
| 3 | Numpad | left thumb hold (`LT_TH L_NUM ESC`, pos 31), or `to L_NUM` from Navigate |
| 4 | Mouse | `LT_TH L_MOUSE N` hold (pos 10) |
| 5 | Alpha+ | right thumb hold (`LT_TH L_ALPHAP RET`, pos 33), or `lt L_ALPHAP N0` on Numpad (pos 33) |
| 6 | Navigate | right thumb hold (`LT_TH L_NAV TAB`, pos 32) |
| 7 | Vim | `lt L_VIM B` (pos 14) |
| 8 | Functions | `to L_FUNC` from Navigate |
| 9 | B (Bluetooth/system) | `to L_B` from Navigate |
| 10 | Hex | `LT_TH L_HEX SE_PLUS` on Numpad (pos 19) |
| 11 | Mouse fast | left thumb hold (pos 31) on Mouse |
| 12 | Mouse slow | left thumb hold (pos 30) on Mouse |

`L_MAIN` always equals `L_GRAPHMOD` (layer 0); `&to L_MAIN` on the Numpad, Mouse, Navigate, Functions and B layers is the way back. The only combo defined is `combo_esc`: positions `1+2` within 40 ms sends `ESC`.

### Layer lock

Position 21 (`M` on the base layer) is a lock key on the Numpad, Mouse,
Navigate and Vim layers: `&tog L_NUM`, `&tog L_MOUSE`, `&tog L_NAV`,
`&tog L_VIM`. Hold the layer's activation key, tap position 21, release the
hold — the layer stays on; tap it again to drop back to Graphmod.

This relies on ZMK's layer *locking* ([zmk#2717](https://github.com/zmkfirmware/zmk/pull/2717)):
`&to` and `&tog` mark a layer locked, and a locked layer ignores deactivation
from non-locking behaviors such as the `&mo` inside `LT_TH`/`&lt`. It is not in
v0.3, which is why `config/west.yml` tracks ZMK `main`. Custom layer behaviors
opt in with a `locking;` property; `&mo` deliberately does not lock.

### Mouse speed

Layers 11 (`L_MFAST`) and 12 (`L_MSLOW`) hold nothing but `&trans` — they exist
so the pointing input listeners can scale events while one is held from the
Mouse layer. The scaling lives in the `&mmv_input_listener` / `&msc_input_listener`
overrides near the top of `kibard.keymap`; the two numbers are
`<multiplier divisor>` (16 max each), and they are the only place to tune speed.

### Home row mods

`HML` (left hand) and `HMR` (right hand) are `zmk,behavior-hold-tap` with `flavor = "balanced"`, `tapping-term-ms = 250`, `quick-tap-ms = 175`, `require-prior-idle-ms = 150`, `hold-trigger-on-release`, and positional `hold-trigger-key-positions` restricting each to the opposite hand. Home row mod order, index→pinky (inner to outer): Alt / Ctrl / Shift.

### Swedish key defines

All `SE_*` macros at the top of `kibard.keymap` map Swedish characters and symbols to their positions on a Swedish keyboard layout (e.g. `SE_AA`, `SE_ADIA`, `SE_OO` for å, ä, ö). On the base layer å/ä/ö sit directly on keys (`SE_AA` at pos 9, `SE_ADIA` at pos 27, `SE_OO` at pos 29).

### Vim macros

The Vim layer provides keyboard macros for `:w`, `:w!`, `:q`, `:q!`, `:qa`, `:Gwrite`, and `Ctrl+W` window navigation (h/j/k/l).

### Staying in sync with the Voyager (Oryx)

The Kibård keymap is a hand-port of a ZSA Voyager layout kept in Oryx
(`ORYX_LAYOUT_ID`, default `6ye0X`). `tools/sync-oryx.py` fetches that layout
from Oryx's public GraphQL API, folds the Voyager's 52 keys onto the Kibård's
34 positions, and reports what moved:

| Command | Purpose |
|---------|---------|
| `tools/sync-oryx.py` | Keys changed in Oryx since the last sync, with suggested ZMK bindings. Exits 1 if any. |
| `tools/sync-oryx.py snapshot` | Record the current Oryx layout as ported — run after editing the keymap, commit alongside. |
| `tools/sync-oryx.py show [N]` | Draw an Oryx layer in Kibård geometry. |
| `tools/sync-oryx.py compare` | Full Oryx-vs-`kibard.keymap` audit (`--hide-blank` drops `&none`/`&trans` noise). |

`tools/oryx-snapshot.json` is the last-synced state; it is the diff's baseline
and belongs in the commit that ports the change.

Two tables in the script encode the port and are asserted on every run, so a
rename or reorder in Oryx fails loudly instead of diffing the wrong layers:

- `POSITION_MAP` — Voyager key index → Kibård position (the Kibård uses the
  Voyager's inner 5 columns of rows 1–3, plus both thumb pairs).
- `LAYER_MAP` — Oryx layer → ZMK layer. The two differ in order: Oryx
  5 Vim → ZMK 7, Oryx 6 Navigate → ZMK 6, Oryx 8 Hex → ZMK 10. ZMK layer 9
  (Bluetooth) has no Oryx counterpart, so nothing maps onto it.
