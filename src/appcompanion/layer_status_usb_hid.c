#include "layer_status_usb_hid.h"
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/usb/class/usb_hid.h>
#include <zephyr/usb/usb_device.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>
#include <zmk/usb.h>

#define RAW_EPSIZE 32
#define PAYLOAD_MARK 0x90
#define PAYLOAD_BEGIN 24

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

static const struct device *hid_dev;
static bool usb_ready = false;

static K_SEM_DEFINE(hid_sem, 1, 1);
static uint8_t report_buf[RAW_EPSIZE]; // Static buffer to avoid stack issues

static void in_ready_cb(const struct device *dev) { k_sem_give(&hid_sem); }

static const struct hid_ops ops = {
    .int_in_ready = in_ready_cb,
};

static void send_layer_report(uint8_t layer) {
  if (hid_dev == NULL) {
    LOG_WRN("USB HID: hid_dev is NULL");
    return;
  }
  if (!usb_ready) {
    LOG_WRN("USB HID: not ready yet");
    return;
  }

  k_sem_take(&hid_sem, K_MSEC(30));

  memset(report_buf, 0x00, RAW_EPSIZE);
  report_buf[PAYLOAD_BEGIN] = PAYLOAD_MARK;
  report_buf[PAYLOAD_BEGIN + 1] = layer;

  int ret = hid_int_ep_write(hid_dev, report_buf, RAW_EPSIZE, NULL);
  if (ret < 0 && ret != -EAGAIN) {
    LOG_ERR("USB HID: failed to send: %d", ret);
    k_sem_give(&hid_sem);
  }
}

static int layer_status_hid_init(const struct device *dev) {
  hid_dev = device_get_binding("HID_1");
  if (hid_dev == NULL) {
    hid_dev = device_get_binding("HID_2");
  }

  if (hid_dev == NULL) {
    LOG_ERR("USB HID: No secondary HID device available");
    LOG_ERR("USB HID: Ensure CONFIG_USB_HID_DEVICE_COUNT=2 in your config");
    return 0;
  }

  LOG_INF("USB HID: Found device at %p", hid_dev);

  const struct device *hid0 = device_get_binding("HID_0");
  if (hid0 == hid_dev) {
    LOG_ERR("USB HID: HID_1 is same as HID_0! Device count issue.");
    return 0;
  }
  LOG_INF("USB HID: HID_0=%p, our device=%p (different: good)", hid0, hid_dev);

  usb_hid_register_device(hid_dev, layer_status_hid_report_desc,
                          sizeof(layer_status_hid_report_desc), &ops);

  usb_hid_init(hid_dev);

  k_sleep(K_MSEC(500));
  usb_ready = true;

  LOG_INF("USB HID: Initialized and ready");
  return 0;
}

static uint8_t last_layer = 255;

static int layer_status_hid_event_listener(const zmk_event_t *eh) {
  const struct zmk_layer_state_changed *ev = as_zmk_layer_state_changed(eh);
  if (ev == NULL) {
    return -ENOTSUP;
  }

  uint8_t highest_layer = zmk_keymap_highest_layer_active();

  if (highest_layer == last_layer) {
    return 0;
  }
  last_layer = highest_layer;

  send_layer_report(highest_layer);

  return 0;
}

ZMK_LISTENER(layer_status_hid, layer_status_hid_event_listener);
ZMK_SUBSCRIPTION(layer_status_hid, zmk_layer_state_changed);

SYS_INIT(layer_status_hid_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
