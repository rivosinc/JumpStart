/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

typedef enum {
  AMOSWAP_ACQUIRE,
  AMOSWAP_RELEASE,
} amoswapKind_t;

#define _swap_atomic(__val, __new_value, __kind)                               \
  ({                                                                           \
    uint64_t result;                                                           \
    switch (__kind) {                                                          \
    case AMOSWAP_RELEASE:                                                      \
      __asm__ __volatile__("amoswap.d.rl %0, %2, %1"                           \
                           : "=r"(result), "+A"(*__val)                        \
                           : "r"(__new_value)                                  \
                           : "memory");                                        \
      break;                                                                   \
    case AMOSWAP_ACQUIRE:                                                      \
      __asm__ __volatile__("amoswap.d.aq %0, %2, %1"                           \
                           : "=r"(result), "+A"(*__val)                        \
                           : "r"(__new_value)                                  \
                           : "memory");                                        \
      break;                                                                   \
    default:                                                                   \
      goto fail;                                                               \
    }                                                                          \
    result;                                                                    \
  })

#define _acquire_lock(__lock, __swap_atomic)                                   \
  ({                                                                           \
    disable_checktc();                                                         \
    while (1) {                                                                \
      if (*(volatile uint64_t *)__lock) {                                      \
        continue;                                                              \
      }                                                                        \
      if (__swap_atomic(__lock, 1, AMOSWAP_ACQUIRE) == 0) {                    \
        break;                                                                 \
      }                                                                        \
    }                                                                          \
    enable_checktc();                                                          \
  })

#define _release_lock(__lock, __swap_atomic)                                   \
  __swap_atomic(__lock, 0, AMOSWAP_RELEASE)
