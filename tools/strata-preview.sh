#!/usr/bin/env bash
# Preview the left half's nice!view screen (src/strata) for every layer in
# config/kibard.keymap: builds the drawing code for this computer and writes
# one PNG with a screen per layer, light pixels on black as on the keyboard.
#
#   tools/strata-preview.sh [OUT.png]      default: strata-preview.png
#
# Extra names to try can be given in STRATA_NAMES, separated by commas:
#   STRATA_NAMES="Mouse fast,Supercalifragilistic" tools/strata-preview.sh
#
# Needs a C compiler and Pillow.
set -euo pipefail

repo=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
out=${1:-strata-preview.png}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

cc -std=c11 -Wall -Wextra -Werror -I"$repo/src/strata" -o "$work/preview" \
    "$repo/tools/strata-preview.c" "$repo/src/strata/draw.c" "$repo/src/strata/assets.c"

i=0
while IFS= read -r name; do
    "$work/preview" "$i" "$name" > "$work/$(printf %03d "$i").pbm"
    i=$((i + 1))
done < <(
    sed -n 's/^ *display-name = "\(.*\)";/\1/p' "$repo/config/kibard.keymap"
    tr ',' '\n' <<< "${STRATA_NAMES:-}" | sed '/^$/d'
)

python3 -I - "$work" "$out" <<'PY'
import pathlib, sys
from PIL import Image, ImageOps
work, out = pathlib.Path(sys.argv[1]), sys.argv[2]
screens = [ImageOps.invert(Image.open(p).convert("L")) for p in sorted(work.glob("*.pbm"))]
gap, scale = 4, 3
sheet = Image.new("L", (len(screens) * (68 + gap) + gap, 160 + 2 * gap), 96)
for i, s in enumerate(screens):
    sheet.paste(s, (gap + i * (68 + gap), gap))
sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(out)
print(f"wrote {out} ({len(screens)} screens)")
PY
