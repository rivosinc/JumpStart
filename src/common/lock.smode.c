/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "lock.h"
#include "jumpstart.h"
#include "lock.smode.h"

__attr_stext static uint64_t swap_atomic(uint64_t *val, uint64_t new_value,
                                         amoswapKind_t kind) {
  return _swap_atomic(val, new_value, kind);

fail:
  jumpstart_smode_fail();
}

__attr_stext void acquire_lock(spinlock_t *lock) {
  _acquire_lock(lock, swap_atomic);
}

__attr_stext void release_lock(spinlock_t *lock) {
  _release_lock(lock, swap_atomic);
}
