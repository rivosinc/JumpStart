/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdint.h>

#include "cpu_bits.h"
#include "delay.h"
#include "jumpstart.h"
#include "time.mmode.h"

__attr_mtext void delay_us_from_mmode(uint32_t delay_in_useconds) {
  _delay_us(delay_in_useconds);
}
