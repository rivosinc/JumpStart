// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart.h"
#include "jumpstart_defines.h"
#include <inttypes.h>

void putch(char c);

__attribute__((section(".jumpstart.text.smode"))) __attribute__((noreturn)) void
putch(char c) {
  // Implement putch code here
  (void)c;
  jumpstart_smode_fail();
}
