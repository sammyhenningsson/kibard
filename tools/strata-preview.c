/*
 * Host build of the Strata nice!view drawing code (src/strata/draw.c), for
 * previews: prints the central half's screen as a PBM image (68x160, portrait)
 * for one layer name. Run through tools/strata-preview.sh.
 *
 *   strata-preview INDEX NAME > screen.pbm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "draw.h"

static bool pixels[SV_HEIGHT][SV_WIDTH];

void sv_px(int x, int y, bool on) {
    if (x >= 0 && x < SV_WIDTH && y >= 0 && y < SV_HEIGHT) {
        pixels[y][x] = on;
    }
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s INDEX NAME\n", argv[0]);
        return 2;
    }
    struct sv_state state = {
        .battery = 80,
        .output = SV_OUTPUT_BLE,
        .profile_index = 0,
        .profile_count = 5,
        .connected = true,
        .bonded = true,
        .layer_index = atoi(argv[1]),
    };
    strncpy(state.layer_name, argv[2], SV_LAYER_NAME_LEN);
    sv_render(&state);

    printf("P1\n%d %d\n", SV_WIDTH, SV_HEIGHT);
    for (int y = 0; y < SV_HEIGHT; y++) {
        for (int x = 0; x < SV_WIDTH; x++) {
            putchar(pixels[y][x] ? '1' : '0');
        }
        putchar('\n');
    }
    return 0;
}
