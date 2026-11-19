/*
 * Strata, a vertical nice!view status screen: drawing. See draw.h.
 *
 * Central half, top to bottom:
 *
 *   connection icon (USB / Bluetooth) and link status, in the top corners
 *   one circle per Bluetooth profile, the selected one filled
 *   the active layer's name, wrapped over as many lines as it needs
 *   battery: five cells, or a bolt while charging
 *
 * Peripheral half: link icon and status, a field of swell lines, battery.
 *
 * Integer arithmetic only: the keyboard builds without an FPU.
 */

#include <stddef.h>

#include "assets.h"
#include "draw.h"

#define OUTPUT_H 21
#define OUTPUT_INSET 0
#define ROW_OUTPUT 0
#define ROW_PROFILES (ROW_OUTPUT + OUTPUT_H + 8)
#define ROW_BATTERY (SV_HEIGHT - 12)

/* Width of the battery icon without its terminal. */
#define BATTERY_BODY 25

#define MAX_PROFILES 5

static void draw_bitmap(int x, int y, int width, int height, const uint8_t *data) {
    int stride = (width + 7) / 8;
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            if (data[row * stride + col / 8] & (0x80 >> (col % 8))) {
                sv_px(x + col, y + row, true);
            }
        }
    }
}

static void draw_icon(int x, int y, const struct sv_icon *icon) {
    draw_bitmap(x, y, icon->width, icon->height, icon->data);
}

/* Draw an icon after clearing `border` pixels around each of its pixels. */
static void draw_icon_cutout(int x, int y, const struct sv_icon *icon, int border) {
    int stride = (icon->width + 7) / 8;
    for (int row = 0; row < icon->height; row++) {
        for (int col = 0; col < icon->width; col++) {
            if (!(icon->data[row * stride + col / 8] & (0x80 >> (col % 8)))) {
                continue;
            }
            for (int dy = -border; dy <= border; dy++) {
                for (int dx = -border; dx <= border; dx++) {
                    sv_px(x + col + dx, y + row + dy, false);
                }
            }
        }
    }
    draw_icon(x, y, icon);
}

static void draw_rect(int x, int y, int width, int height) {
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            sv_px(x + col, y + row, true);
        }
    }
}

static void draw_output(const struct sv_state *state) {
    const struct sv_icon *icon = NULL;
    const struct sv_icon *status = NULL;

    if (state->peripheral) {
        icon = &sv_icon_bluetooth;
        status = state->connected ? &sv_icon_linked : &sv_icon_unlinked;
    } else if (state->output == SV_OUTPUT_USB) {
        icon = &sv_icon_usb;
        status = &sv_icon_linked;
    } else if (state->output == SV_OUTPUT_BLE) {
        icon = &sv_icon_bluetooth;
        if (!state->bonded) {
            status = &sv_icon_pairing;
        } else {
            status = state->connected ? &sv_icon_linked : &sv_icon_unlinked;
        }
    }
    if (icon == NULL) {
        return;
    }

    /* One in each top corner, centred on the row. */
    draw_icon(OUTPUT_INSET, ROW_OUTPUT + (OUTPUT_H - icon->height) / 2, icon);
    draw_icon(SV_WIDTH - OUTPUT_INSET - status->width,
              ROW_OUTPUT + (OUTPUT_H - status->height) / 2, status);
}

static void draw_profiles(const struct sv_state *state) {
    int count = state->profile_count > MAX_PROFILES ? MAX_PROFILES : state->profile_count;
    if (count <= 0) {
        return;
    }
    int size = sv_icon_profile.width;
    /* Spread evenly over the full width: the first and last circles touch
     * the sides. Five 8 px circles leave exact 7 px gaps. */
    int span = SV_WIDTH - size;

    for (int i = 0; i < count; i++) {
        int x = count > 1 ? i * span / (count - 1) : span / 2;
        draw_icon(x, ROW_PROFILES,
                  i == state->profile_index ? &sv_icon_profile_active : &sv_icon_profile);
    }
}

/*
 * Layer name, in the pixel font from assets/font.txt, centred in the band
 * between the profiles and the battery. Lines break at spaces; a word wider
 * than the screen is split into pieces of about equal width ("Naviga", "te"
 * would read worse than "Navi", "gate"). The band holds as many lines as fit
 * and the rest is cut off.
 */
#define NAME_MAX_GLYPHS SV_LAYER_NAME_LEN
#define NAME_MAX_LINES 8
/* Lines overlap by this much: the font's top rows are only for the ring on
 * Å, and its bottom rows only for descenders. */
#define NAME_LINE_OVERLAP 3

static const struct sv_glyph *find_glyph(uint32_t codepoint) {
    const struct sv_font *font = &sv_font_name;
    int lo = 0, hi = font->count - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (font->glyphs[mid].codepoint == codepoint) {
            return &font->glyphs[mid];
        }
        if (font->glyphs[mid].codepoint < codepoint) {
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return NULL;
}

/* Decode UTF-8 into glyphs; returns the count. Unknown characters become "?". */
static int name_glyphs(const char *text, const struct sv_glyph **out) {
    const uint8_t *p = (const uint8_t *)text;
    int n = 0;
    while (*p != '\0' && n < NAME_MAX_GLYPHS) {
        uint32_t cp;
        int extra;
        if (*p < 0x80) {
            cp = *p;
            extra = 0;
        } else if ((*p & 0xe0) == 0xc0) {
            cp = *p & 0x1f;
            extra = 1;
        } else if ((*p & 0xf0) == 0xe0) {
            cp = *p & 0x0f;
            extra = 2;
        } else {
            cp = *p & 0x07;
            extra = 3;
        }
        p++;
        for (; extra > 0 && (*p & 0xc0) == 0x80; extra--, p++) {
            cp = (cp << 6) | (*p & 0x3f);
        }
        const struct sv_glyph *glyph = find_glyph(cp);
        if (glyph == NULL) {
            glyph = find_glyph('?');
        }
        if (glyph != NULL) {
            out[n++] = glyph;
        }
    }
    return n;
}

static bool is_space(const struct sv_glyph *glyph) { return glyph->codepoint == ' '; }

/* Pen positions are in 1/16 px; a glyph's first column lands on the pixel
 * nearest its pen position. */
#define PEN_PX(pen) (((pen) + 8) >> 4)

/* Width of glyphs [from, to) as drawn, from the first glyph's leftmost
 * column to the last one's rightmost. */
static int span_width(const struct sv_glyph **glyphs, int from, int to) {
    if (from >= to) {
        return 0;
    }
    int pen = 0;
    for (int i = from; i < to - 1; i++) {
        pen += glyphs[i]->advance;
    }
    int right = PEN_PX(pen) + glyphs[to - 1]->left + glyphs[to - 1]->width;
    return right - glyphs[from]->left;
}

/* End of a piece of the over-wide word [from, word_end) that fits one line,
 * aiming for pieces of equal width. Always takes at least one glyph. */
static int split_word(const struct sv_glyph **glyphs, int from, int word_end) {
    int total = span_width(glyphs, from, word_end);
    int pieces = (total + SV_WIDTH - 1) / SV_WIDTH;
    int target = total / pieces;
    int end = from + 1;
    while (end < word_end && span_width(glyphs, from, end + 1) <= SV_WIDTH &&
           span_width(glyphs, from, end) + PEN_PX(glyphs[end]->advance) / 2 <= target) {
        end++;
    }
    return end;
}

static void draw_glyph(int x, int y, const struct sv_glyph *glyph) {
    draw_bitmap(x + glyph->left, y, glyph->width, sv_font_name.height,
                sv_font_name.data + glyph->offset);
}

static void draw_layer_name(const struct sv_state *state, int band_top, int band_bottom) {
    char number[4];
    const char *text = state->layer_name;
    if (text[0] == '\0') {
        /* No display-name in the keymap: show the layer index. */
        int index = state->layer_index;
        int i = 0;
        if (index >= 100) {
            number[i++] = '0' + index / 100;
        }
        if (index >= 10) {
            number[i++] = '0' + index / 10 % 10;
        }
        number[i++] = '0' + index % 10;
        number[i] = '\0';
        text = number;
    }

    const struct sv_glyph *glyphs[NAME_MAX_GLYPHS];
    int count = name_glyphs(text, glyphs);

    /* Break into lines: [starts[i], ends[i]) */
    int starts[NAME_MAX_LINES], ends[NAME_MAX_LINES];
    int pitch = sv_font_name.height - NAME_LINE_OVERLAP;
    int max_lines = (band_bottom - band_top - sv_font_name.height) / pitch + 1;
    if (max_lines > NAME_MAX_LINES) {
        max_lines = NAME_MAX_LINES;
    }
    int lines = 0;
    int pos = 0;
    while (lines < max_lines) {
        while (pos < count && is_space(glyphs[pos])) {
            pos++;
        }
        if (pos >= count) {
            break;
        }
        int end = pos;
        while (end < count) {
            /* Next word, with the spaces before it. */
            int word = end;
            while (word < count && is_space(glyphs[word])) {
                word++;
            }
            int word_end = word;
            while (word_end < count && !is_space(glyphs[word_end])) {
                word_end++;
            }
            if (span_width(glyphs, pos, word_end) <= SV_WIDTH) {
                end = word_end;
            } else {
                if (end == pos) {
                    end = split_word(glyphs, pos, word_end);
                }
                break;
            }
        }
        starts[lines] = pos;
        ends[lines] = end;
        lines++;
        pos = end;
    }
    if (lines == 0) {
        return;
    }

    int height = sv_font_name.height + (lines - 1) * pitch;
    int y = band_top + (band_bottom - band_top - height) / 2;
    for (int line = 0; line < lines; line++, y += pitch) {
        int x = (SV_WIDTH - span_width(glyphs, starts[line], ends[line])) / 2 -
                glyphs[starts[line]]->left;
        int pen = 0;
        for (int i = starts[line]; i < ends[line]; i++) {
            draw_glyph(x + PEN_PX(pen), y, glyphs[i]);
            pen += glyphs[i]->advance;
        }
    }
}

static void draw_battery(const struct sv_state *state) {
    int x = (SV_WIDTH - sv_icon_battery.width) / 2;
    draw_icon(x, ROW_BATTERY, &sv_icon_battery);

    if (state->charging) {
        /* The bolt replaces the cells, with a clear pixel around it where it
         * meets the outline. */
        draw_icon_cutout(x + (BATTERY_BODY - sv_icon_charging.width) / 2,
                         ROW_BATTERY + (sv_icon_battery.height - sv_icon_charging.height) / 2,
                         &sv_icon_charging, 1);
        return;
    }

    /* Five cells of 20 % each; the first stays lit until the battery is
     * truly empty. */
    int level = state->battery > 100 ? 100 : state->battery;
    int cells = (level + 19) / 20;
    for (int i = 0; i < cells; i++) {
        draw_rect(x + 3 + i * 4, ROW_BATTERY + 3, 3, 6);
    }
}

/*
 * Swell: wavy lines stacked down the screen, nearer lines hiding the ones
 * behind them. Each line is the sum of three sine waves of different lengths
 * that move at different speeds as `frame` advances, and the whole field
 * drifts down one pixel every two frames. SV_SWELL_FRAMES frames make a
 * seamless loop.
 *
 * Angles are 16-bit, 65536 to a turn; heights are in 1/64 pixel.
 */
#define SWELL_TOP 28
#define SWELL_BOTTOM 140 /* first row below the field */
#define SWELL_STEP 8     /* rows between lines */
#define SWELL_PHASES 8   /* lines until the shapes repeat */
#define SWELL_FIRST (-2)
#define SWELL_LAST 26

#define TURN 65536
#define FP 64

/* sin() over one turn in 256 steps, scaled to +-127. */
static const int8_t sine[256] = {
       0,    3,    6,    9,   12,   16,   19,   22,   25,   28,   31,   34,
      37,   40,   43,   46,   49,   51,   54,   57,   60,   63,   65,   68,
      71,   73,   76,   78,   81,   83,   85,   88,   90,   92,   94,   96,
      98,  100,  102,  104,  106,  107,  109,  111,  112,  113,  115,  116,
     117,  118,  120,  121,  122,  122,  123,  124,  125,  125,  126,  126,
     126,  127,  127,  127,  127,  127,  127,  127,  126,  126,  126,  125,
     125,  124,  123,  122,  122,  121,  120,  118,  117,  116,  115,  113,
     112,  111,  109,  107,  106,  104,  102,  100,   98,   96,   94,   92,
      90,   88,   85,   83,   81,   78,   76,   73,   71,   68,   65,   63,
      60,   57,   54,   51,   49,   46,   43,   40,   37,   34,   31,   28,
      25,   22,   19,   16,   12,    9,    6,    3,    0,   -3,   -6,   -9,
     -12,  -16,  -19,  -22,  -25,  -28,  -31,  -34,  -37,  -40,  -43,  -46,
     -49,  -51,  -54,  -57,  -60,  -63,  -65,  -68,  -71,  -73,  -76,  -78,
     -81,  -83,  -85,  -88,  -90,  -92,  -94,  -96,  -98, -100, -102, -104,
    -106, -107, -109, -111, -112, -113, -115, -116, -117, -118, -120, -121,
    -122, -122, -123, -124, -125, -125, -126, -126, -126, -127, -127, -127,
    -127, -127, -127, -127, -126, -126, -126, -125, -125, -124, -123, -122,
    -122, -121, -120, -118, -117, -116, -115, -113, -112, -111, -109, -107,
    -106, -104, -102, -100,  -98,  -96,  -94,  -92,  -90,  -88,  -85,  -83,
     -81,  -78,  -76,  -73,  -71,  -68,  -65,  -63,  -60,  -57,  -54,  -51,
     -49,  -46,  -43,  -40,  -37,  -34,  -31,  -28,  -25,  -22,  -19,  -16,
     -12,   -9,   -6,   -3,
};

static int sin127(int32_t angle) { return sine[((uint32_t)angle >> 8) & 0xff]; }

/* Height of line `k` above its baseline at column x, in 1/64 pixel. */
static int swell_height(int x, int k, int frame) {
    int32_t t = frame * (TURN / (SV_SWELL_FRAMES / 2));
    int32_t line = k * (TURN / SWELL_PHASES);

    int swing = (FP * 24 / 10) + (FP * 14 / 10) * sin127(t + line) / 127;
    int height = FP * 35 / 10;
    height += swing * sin127(x * TURN / 40 + line - t) / 127;
    height += FP * sin127(x * TURN / 20 - line + 2 * t) / 127;
    height += (FP * 14 / 10) * sin127(x * TURN / 68 + 2 * line + t) / 127;
    return height;
}

/* Lines thin out to dashes over the last rows before the icons. */
static bool swell_visible(int x, int y) {
    int edge = y - SWELL_TOP < SWELL_BOTTOM - 1 - y ? y - SWELL_TOP : SWELL_BOTTOM - 1 - y;
    if (edge < 0) {
        return false;
    }
    int dash = edge < 5 ? 2 : edge < 10 ? 3 : 4;
    return x % 4 < dash;
}

static void draw_swell(int frame) {
    /* Highest row drawn so far in each column: lines behind stay under it. */
    int16_t horizon[SV_WIDTH];
    for (int x = 0; x < SV_WIDTH; x++) {
        horizon[x] = SWELL_BOTTOM;
    }

    frame %= SV_SWELL_FRAMES;
    if (frame < 0) {
        frame += SV_SWELL_FRAMES;
    }

    /* Nearest line first. */
    for (int k = SWELL_FIRST; k <= SWELL_LAST; k++) {
        int base = SV_HEIGHT + 6 - k * SWELL_STEP + frame / 2;
        int16_t rows[SV_WIDTH];

        for (int x = 0; x < SV_WIDTH; x++) {
            rows[x] = base - ((swell_height(x, k, frame) + FP / 2) >> 6);
        }
        for (int x = 0; x < SV_WIDTH; x++) {
            /* Join to the previous column so the line has no gaps. */
            int from = rows[x], to = rows[x];
            if (x > 0 && rows[x - 1] < rows[x] - 1) {
                from = rows[x - 1] + 1;
            } else if (x > 0 && rows[x - 1] > rows[x] + 1) {
                to = rows[x - 1] - 1;
            }
            for (int row = from; row <= to; row++) {
                if (row < horizon[x] && swell_visible(x, row)) {
                    sv_px(x, row, true);
                }
            }
        }
        for (int x = 0; x < SV_WIDTH; x++) {
            if (rows[x] < horizon[x]) {
                horizon[x] = rows[x];
            }
        }
    }
}

void sv_render(const struct sv_state *state) {
    draw_output(state);
    draw_battery(state);

    if (state->peripheral) {
        draw_swell(state->frame);
    } else {
        draw_profiles(state);
        draw_layer_name(state, ROW_PROFILES + sv_icon_profile.height + 2, ROW_BATTERY - 2);
    }
}
