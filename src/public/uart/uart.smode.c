/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"
#include "jumpstart_defines.h"
#include <inttypes.h>

void setup_uart(void);

__attr_stext __attribute__((noreturn)) void putch(char c) {
  // Implement putch code here
  (void)c;
  jumpstart_smode_fail();
}

__attr_stext void setup_uart(void) {
  // Implement Uart Setup code here
}
