#!/usr/bin/env python3
"""Rasterise a TrueType/OpenType font into src/strata/assets/font.txt.

The nice!view screen (src/strata) draws layer names from a 1-bit pixel font.
This script makes that font from an outline font, without anti-aliasing, as
text with one character per pixel, so single glyphs can be touched up by hand
afterwards. Run tools/strata-gen-assets.py after either step to regenerate the
C data.

  tools/strata-gen-font.py FONT SIZE [--tracking N]

The font checked in was made with

  tools/strata-gen-font.py \\
      /usr/share/fonts/TTF/NotoSansNerdFontPropo-ExtraCondensedBold.ttf 17

(Noto Sans ExtraCondensed Bold as shipped in Manjaro's ttf-noto-nerd; the Latin
glyphs are Noto Sans's own). At 17 px every word in config/kibard.keymap's
layer names fits the 68 px screen width on one line; "Graphmod" fills it
exactly. Rerunning it overwrites any hand edits in font.txt.

Needs Pillow.
"""

import argparse
import pathlib

from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "strata" / "assets" / "font.txt"

# Printable ASCII and the Swedish letters. Anything else in a layer name is
# drawn as "?".
CHARS = [chr(c) for c in range(0x20, 0x7F)] + list("ÅÄÖåäöÉéÜü")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("font", type=pathlib.Path)
    ap.add_argument("size", type=int, help="pixel size passed to FreeType")
    ap.add_argument("--tracking", type=int, default=0,
                    help="pixels added to every advance (negative tightens)")
    args = ap.parse_args()

    font = ImageFont.truetype(str(args.font), args.size)
    canvas = (args.size * 3, args.size * 3)
    origin = args.size  # room for negative side bearings and accents

    glyphs = []
    for ch in CHARS:
        im = Image.new("1", canvas, 0)
        draw = ImageDraw.Draw(im)
        draw.fontmode = "1"  # no anti-aliasing: every pixel is on or off
        draw.text((origin, origin), ch, font=font, fill=1)
        # Advances keep their fraction, as 1/16 px, the way FreeType places
        # glyphs along a line; rounding each one adds a pixel every few letters.
        advance = round((font.getlength(ch) + args.tracking) * 16) / 16
        glyphs.append((ch, im, im.getbbox(), advance))

    # Every glyph gets the same rows: from the highest pixel of any glyph
    # (the ring on Å) to the lowest (descenders).
    top = min(b[1] for _, _, b, _ in glyphs if b)
    bottom = max(b[3] for _, _, b, _ in glyphs if b)
    height = bottom - top

    out = [
        "# Pixel font for the layer name on the Strata nice!view screen, one",
        "# pixel per character: '#' is a lit pixel, '.' is background.",
        "#",
        f"# Rasterised by tools/strata-gen-font.py from {args.font.name} at {args.size} px"
        + (f", tracking {args.tracking}" if args.tracking else "") + ".",
        "# Noto Sans: Copyright 2022 The Noto Project Authors, SIL Open Font",
        "# License 1.1 (https://openfontlicense.org). Hand edits are fine; run",
        "# tools/strata-gen-assets.py afterwards.",
        "#",
        "# Each glyph is 'glyph U+XXXX <left> <advance>' and then one row per line",
        "# of the font's height. Rows cover the glyph's ink only: <left> is where",
        "# the first column sits relative to the pen, <advance> is how far the pen",
        "# moves on, in pixels with a fraction (to 1/16).",
        "",
        f"font {height}",
        "",
    ]
    for ch, im, bbox, advance in glyphs:
        if bbox is None:  # blank, such as the space
            left, x0, x1 = 0, 0, 1
        else:
            x0, x1 = bbox[0], bbox[2]
            left = x0 - origin
        out.append(f"glyph U+{ord(ch):04X} {left} {advance:g}  {ch if ch != ' ' else 'space'}")
        for y in range(top, bottom):
            out.append("".join("#" if im.getpixel((x, y)) else "." for x in range(x0, x1)))
        out.append("")

    OUT.write_text("\n".join(out))
    print(f"wrote {OUT} ({len(glyphs)} glyphs, {height} px high)")


if __name__ == "__main__":
    main()
