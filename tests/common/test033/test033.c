// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart.h"

int umode_main(void) __attribute__((section(".text.umode"), noreturn));

int main(void) {
  return run_function_in_umode((uint64_t)umode_main);
}

int umode_main(void) {
  jumpstart_umode_fail();
}
