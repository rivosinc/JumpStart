// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "heap_functions.supervisor.h"
#include "jumpstart_functions.h"
#include "tablewalk_functions.supervisor.h"

extern uint64_t _JUMPSTART_SUPERVISOR_HEAP_START;
extern uint64_t _JUMPSTART_SUPERVISOR_HEAP_END;

#define MAGIC_VALUE8  0xca
#define MAGIC_VALUE16 0xcafe
#define MAGIC_VALUE32 0xcafecafe
#define MAGIC_VALUE64 0xcafecafecafecafe

int main(void) {
  const uint64_t max_heap_size = (uint64_t)&_JUMPSTART_SUPERVISOR_HEAP_END -
                                 (uint64_t)&_JUMPSTART_SUPERVISOR_HEAP_START;

  uint8_t *x8 = malloc(sizeof(uint8_t));
  if (x8 == 0) {
    return DIAG_FAILED;
  }

  *x8 = MAGIC_VALUE8;
  if (*x8 != MAGIC_VALUE8) {
    return DIAG_FAILED;
  }

  uint16_t *x16 = malloc(sizeof(uint16_t));
  if (x16 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x16 & 0x1) != 0) {
    return DIAG_FAILED;
  }

  *x16 = MAGIC_VALUE16;
  if (*x16 != MAGIC_VALUE16) {
    return DIAG_FAILED;
  }

  uint32_t *x32 = malloc(sizeof(uint32_t));
  if (x32 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x32 & 0x3) != 0) {
    return DIAG_FAILED;
  }

  *x32 = MAGIC_VALUE32;
  if (*x32 != MAGIC_VALUE32) {
    return DIAG_FAILED;
  }

  uint64_t *x64 = malloc(sizeof(uint64_t));
  if (x64 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x64 & 0x7) != 0) {
    return DIAG_FAILED;
  }

  *x64 = MAGIC_VALUE64;
  if (*x64 != MAGIC_VALUE64) {
    return DIAG_FAILED;
  }

  free(x8);
  free(x16);
  free(x32);
  free(x64);

  void *y = malloc(max_heap_size / 2);
  if (y == 0) {
    return DIAG_FAILED;
  }

  void *z = malloc(max_heap_size / 2);
  if (z != 0) {
    return DIAG_FAILED;
  }

  free(y);

  z = malloc(max_heap_size / 2);
  if (z == 0) {
    return DIAG_FAILED;
  }

  x64 = malloc(max_heap_size / 2);
  if (x64 != 0) {
    return DIAG_FAILED;
  }

  free(z);

  return DIAG_PASSED;
}
