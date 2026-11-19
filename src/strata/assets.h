/*
 * Strata, a vertical nice!view status screen: 1-bit icons.
 * The data is generated; see tools/strata-gen-assets.py.
 */

#pragma once

#include <stdint.h>

/* Bitmap icon: rows are padded to a whole byte, the most significant bit is
 * the leftmost pixel. */
struct sv_icon {
    uint8_t width;
    uint8_t height;
    const uint8_t *data;
};

/* Pixel font glyph. Rows span the font's full height and only the glyph's ink
 * columns, padded to a whole byte like an icon; `left` places the first
 * column relative to the pen and `advance` moves the pen on, in 1/16 px. */
struct sv_glyph {
    uint16_t codepoint;
    int8_t left;
    uint16_t advance;
    uint8_t width;
    uint16_t offset; /* into sv_font.data */
};

/* Glyphs are sorted by codepoint. */
struct sv_font {
    uint8_t height;
    uint8_t count;
    const struct sv_glyph *glyphs;
    const uint8_t *data;
};

#include "assets_list.h"
