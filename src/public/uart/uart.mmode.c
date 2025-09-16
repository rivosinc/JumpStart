/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"
#include <inttypes.h>

void setup_uart(void);

__attr_mtext __attribute__((noreturn)) void m_putch(char c) {
  // Implement putch code here
  (void)c;
  jumpstart_mmode_fail();
}

__attr_mtext void m_setup_uart(void) {
  // Implement Uart Setup code here
}
