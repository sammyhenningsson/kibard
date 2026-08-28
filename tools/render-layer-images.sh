#!/usr/bin/env bash
# Renders one PNG per keymap layer into companion/images/, for the Keyboard
# Layers App Companion (https://github.com/maatthc/keyboard_layers_app_companion).
# Filenames must match the layer_N mapping in companion/config.ini.
#
# Run tools/install-companion.sh afterwards only if the app clone isn't linked
# up yet — it symlinks these files, so re-rendering is picked up automatically.
#
# Requires: keymap-drawer (venv below) and rsvg-convert (librsvg).
set -euo pipefail

# CDPATH= : a relative `cd` searches CDPATH and echoes the resolved path,
# which would otherwise land in REPO as a second line.
REPO="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYMAP="$REPO/config/kibard.keymap"
CONFIG="$REPO/tools/keymap-drawer.yaml"
KM="${KEYMAP_DRAWER:-$HOME/.local/share/kmdrawer-venv/bin/keymap}"
OUT="${1:-$REPO/companion/images}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Layer name in the keymap -> image basename, in layer-index order (0..8).
LAYERS=(Graphmod:graphmod Symbols:symbols Numpad:numpad Right:right \
        Navigate:navigate Vim:vim Mouse:mouse Functions:functions B:b)

mkdir -p "$OUT"
"$KM" -c "$CONFIG" parse -z "$KEYMAP" -o "$WORK/kibard.yaml"

# The shield isn't in keymap-drawer's layout DB, so describe it explicitly:
# 3 rows x 5 columns per half plus 2 thumbs = 34 keys.
sed -i 's|^layout: .*|layout: {ortho_layout: {split: true, rows: 3, columns: 5, thumbs: 2}}|' \
    "$WORK/kibard.yaml"

# Drop combos: the single 30+31+32 combo is the same on every layer and drawing
# it adds a second, near-empty keyboard diagram to each image.
python3 -c "import sys; p=sys.argv[1]; s=open(p).read(); open(p,'w').write(s.split('combos:')[0].rstrip()+'\n')" \
    "$WORK/kibard.yaml"

for entry in "${LAYERS[@]}"; do
    layer="${entry%%:*}"; name="${entry##*:}"
    "$KM" -c "$CONFIG" draw "$WORK/kibard.yaml" --select-layers "$layer" -o "$WORK/$name.svg"
    rsvg-convert -b white -w 1600 "$WORK/$name.svg" -o "$OUT/kibard-$name.png"
    echo "  $layer -> $OUT/kibard-$name.png"
done
echo "Rendered ${#LAYERS[@]} layer images."
