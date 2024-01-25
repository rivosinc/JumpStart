// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "lock_functions.smode.h"

typedef enum {
  AMOSWAP_ACQUIRE,
  AMOSWAP_RELEASE,
} amoswapKind_t;

__attribute__((section(".jumpstart.text.smode"))) static uint64_t
swap_atomic(uint64_t *val, uint64_t new_value, amoswapKind_t kind) {
  uint64_t result;
  switch (kind) {
  case AMOSWAP_RELEASE:
    __asm__ __volatile__("amoswap.d.rl %0, %2, %1"
                         : "=r"(result), "+A"(*val)
                         : "r"(new_value)
                         : "memory");
    break;
  case AMOSWAP_ACQUIRE:
  default:
    __asm__ __volatile__("amoswap.d.aq %0, %2, %1"
                         : "=r"(result), "+A"(*val)
                         : "r"(new_value)
                         : "memory");
    break;
  }

  return result;
}

__attribute__((section(".jumpstart.text.smode"))) void
acquire_lock(spinlock_t *lock) {
  while (1) {
    if (*(volatile uint64_t *)lock) {
      continue;
    }
    if (swap_atomic(lock, 1, AMOSWAP_ACQUIRE) == 0) {
      break;
    }
  }
}

__attribute__((section(".jumpstart.text.smode"))) void
release_lock(spinlock_t *lock) {
  swap_atomic(lock, 0, AMOSWAP_RELEASE);
}
