// SPDX-License-Identifier: GPL-2.0
/*
 * TB-9707F (Lenovo Legion Y700) build compatibility shims.
 *
 * The published TB-Q706F tree references two symbols whose real providers sit
 * in drivers this defconfig does not build:
 *
 *   - hall_disable_fp_pk : drivers/input/hall_sensor.c
 *                          (CONFIG_SENSORS_HALL, a Lenovo hall-sensor driver)
 *   - usb_is_plugin()    : drivers/input/touchscreen/goodix/goodix_ts_core.c
 *                          (CONFIG_TOUCHSCREEN_GOODIX_BRL, Goodix touch)
 *
 * Their consumers, however, are always built - qpnp-power-on.c, smb5-lib.c and
 * gf_spi.c - so the kernel only links if a definition exists somewhere.
 *
 * These weak fallbacks are honest no-ops rather than driver enablement:
 *   - no hall-sensor driver means the fingerprint power-key workaround stays
 *     off, which is the stock behaviour when the sensor is absent;
 *   - the USB-plugin notification is only consumed by Goodix touch, which this
 *     device does not use (it is a Novatek NVT-ts panel/touch combo); the only
 *     in-tree implementation is itself a stub returning 0.
 *
 * Being weak, they are overridden the moment CONFIG_SENSORS_HALL or
 * CONFIG_TOUCHSCREEN_GOODIX_BRL is enabled.
 */
#include <linux/export.h>
#include <linux/types.h>

bool hall_disable_fp_pk __weak = false;
EXPORT_SYMBOL(hall_disable_fp_pk);

int __weak usb_is_plugin(bool enabled)
{
	return 0;
}
EXPORT_SYMBOL(usb_is_plugin);
