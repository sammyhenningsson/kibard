/*
 * Strata, a vertical nice!view status screen: drawing.
 *
 * The screen is drawn as a 68x160 portrait image, one bit per pixel, straight
 * from bitmap icons: nothing is scaled, rotated or smoothed on the
 * way. sv_render() calls sv_px() for the pixels it sets; the caller clears its
 * buffer first and maps portrait pixels to the panel.
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>

#define SV_WIDTH 68
#define SV_HEIGHT 160

/* Frames in one loop of the peripheral's swell animation. */
#define SV_SWELL_FRAMES 128

/* Longest layer name shown, in bytes of UTF-8; longer names are cut. */
#define SV_LAYER_NAME_LEN 32

enum sv_output {
    SV_OUTPUT_NONE,
    SV_OUTPUT_USB,
    SV_OUTPUT_BLE,
};

struct sv_state {
    bool peripheral;

    uint8_t battery;
    bool charging;

    /* Central: selected output. Peripheral: link to the central half. */
    enum sv_output output;
    int profile_index;
    int profile_count;
    bool connected;
    bool bonded;

    /* Central: highest active layer and its display-name, or "" for none. */
    uint8_t layer_index;
    char layer_name[SV_LAYER_NAME_LEN + 1];

    /* Peripheral: frame of the swell animation, any value. */
    int frame;
};

/* Provided by the caller: set or clear one pixel of the portrait image. */
void sv_px(int x, int y, bool on);

void sv_render(const struct sv_state *state);
