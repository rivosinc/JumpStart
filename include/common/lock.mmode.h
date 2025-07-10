/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once
#include <inttypes.h>
typedef uint64_t spinlock_t;

void m_acquire_lock(spinlock_t *lock);

void m_release_lock(spinlock_t *lock);
