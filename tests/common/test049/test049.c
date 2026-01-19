/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"

void vumode_main(void) __attribute__((section(".text.vumode")));
int vsmode_main(void) __attribute__((section(".text.vsmode")));

int main(void) {
  return run_function_in_vsmode((uint64_t)vsmode_main);
}

int vsmode_main(void) {
  return run_function_in_vumode((uint64_t)vumode_main);
}

void vumode_main(void) {
  jumpstart_vumode_fail();
}
