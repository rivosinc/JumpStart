/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "lock.h"
#include "jumpstart.h"
#include "lock.mmode.h"

__attr_mtext static uint64_t m_swap_atomic(uint64_t *val, uint64_t new_value,
                                           amoswapKind_t kind) {
  return _swap_atomic(val, new_value, kind);

fail:
  jumpstart_mmode_fail();
}

__attr_mtext void m_acquire_lock(spinlock_t *lock) {
  _acquire_lock(lock, m_swap_atomic);
}

__attr_mtext void m_release_lock(spinlock_t *lock) {
  _release_lock(lock, m_swap_atomic);
}
