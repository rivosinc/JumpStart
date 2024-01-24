// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

int umode_main(void) __attribute__((section(".text.user"), noreturn));

int main(void) {
  return run_function_in_umode((uint64_t)umode_main, 0);
}

int umode_main(void) {
  jumpstart_umode_fail();
}
