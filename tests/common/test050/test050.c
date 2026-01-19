/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"

__attribute__((const)) int main(void);

void vsmode_main(void) __attribute__((section(".text.vsmode")));

void vsmode_main(void) {
  jumpstart_vsmode_fail();
}

int main(void) {
  return run_function_in_vsmode((uint64_t)vsmode_main);
}
