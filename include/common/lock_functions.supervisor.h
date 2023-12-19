// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once
#include <inttypes.h>
typedef uint64_t spinlock_t;

void acquire_lock(spinlock_t *lock);

void release_lock(spinlock_t *lock);
