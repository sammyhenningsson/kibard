# Layer display (Keyboard Layers App Companion)

Host-side files for [keyboard_layers_app_companion](https://github.com/maatthc/keyboard_layers_app_companion),
which shows the active Kibård layer on screen. They live here rather than in the
app checkout so a new machine only needs `git clone` of this repo.

| Path | Purpose |
|------|---------|
| `config.ini` | HID identifiers (BLE VID/PID `0x1D50`/`0x615E`) and the layer index → image mapping |
| `images/kibard-*.png` | One rendered image per layer, generated from `config/kibard.keymap` |

The firmware side is `CONFIG_ZMK_LAYER_STATUS_BLE_HID=y` in `config/kibard_left.conf`,
which stuffs the active layer number into the reserved byte of the keyboard HID
report — so this works over BLE *and* USB, on the central half only.

## Setting up a machine

```bash
sudo pacman -Syu --needed python-kivy python-hid python-aiohttp python-zeroconf python-tenacity
git clone https://github.com/maatthc/keyboard_layers_app_companion.git ~/Development/keyboard_layers_app_companion
~/Development/kibård/tools/install-companion.sh
cd ~/Development/keyboard_layers_app_companion && python3 main.py --ble
```

Add `--web` for a browser view on port 1977 instead of the Kivy window.

Do **not** install `python-hidapi` — it conflicts with `python-hid`, and the app
needs the latter's binding. The bundled `Pipfile` is no use on Manjaro either;
Kivy publishes no wheels for the distro's Python.

Reading the keyboard's hidraw node needs a udev rule — without it the app finds
the device but reports `Could not open: unable to open device`:

```bash
sudo tee /etc/udev/rules.d/99-kibard-hidraw.rules <<'EOF'
KERNEL=="hidraw*", KERNELS=="000[35]:1D50:615E.*", TAG+="uaccess", GROUP="input", MODE="0660"
EOF
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=hidraw --action=change
```

You must also be in the `input` group (`sudo usermod -aG input "$USER"`, then log
back in). `uaccess` alone isn't enough for a device that was already enumerated.

The keyboard holds one BLE connection at a time, so the display only updates on
whichever machine currently owns it. To mirror it elsewhere, run the app with
`--ble --server` there and `--client` on the other machine.

## Regenerating the images

After any keymap change:

```bash
tools/render-layer-images.sh   # needs the keymap-drawer venv + rsvg-convert
```

The app picks up the new files immediately (they're symlinks). Adding or
reordering a layer additionally means updating the `LAYERS` array in that script
*and* the `layer_N` entries in `config.ini` — both are ordered by layer index.
