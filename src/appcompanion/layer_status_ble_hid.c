/*
 * Embeds active layer number in keyboard HID report's reserved byte.
 */

#include <dt-bindings/zmk/hid_usage_pages.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zmk/endpoints.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

static uint8_t current_layer = 0;

static int layer_status_embedded_listener(const zmk_event_t *eh) {
  const struct zmk_layer_state_changed *ev = as_zmk_layer_state_changed(eh);
  if (ev == NULL) {
    return -ENOTSUP;
  }

  uint8_t layer = zmk_keymap_highest_layer_active();

  if (layer == current_layer) {
    return 0;
  }
  current_layer = layer;

  struct zmk_hid_keyboard_report *report = zmk_hid_get_keyboard_report();
  report->body._reserved = layer;

  zmk_endpoint_send_report(HID_USAGE_KEY);

  return 0;
}

ZMK_LISTENER(layer_status_embedded, layer_status_embedded_listener);
ZMK_SUBSCRIPTION(layer_status_embedded, zmk_layer_state_changed);
