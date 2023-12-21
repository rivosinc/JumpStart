// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "jumpstart_functions.h"
#include <inttypes.h>

extern void enable_uart(void);
void setup_uart(void);
void putch(char c);

__attribute__((section(".jumpstart.text.machine"))) void setup_uart(void) {
  // Implement Uart Setup code here
}

__attribute__((section(".jumpstart.text.supervisor")))
__attribute__((noreturn)) void
putch(char c) {
  // Implement putch code here
  (void)c;
  jumpstart_supervisor_fail();
}
