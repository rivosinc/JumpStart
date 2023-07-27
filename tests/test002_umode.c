// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include <inttypes.h>

#include "jumpstart_defines.h"

int copy_512_bytes_in_umode(void) __attribute__((section(".text.umode")));
int test_umode(void) __attribute__((section(".text.umode")));

int test_umode(void) {
  if (copy_512_bytes_in_umode() != 0) {
    return 1;
  }

  return 0;
}
