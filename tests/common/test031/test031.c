/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"
#include "lock.smode.h"

#define NUM_ITER 100

spinlock_t lock = 0;

uint8_t last_visitor = 0xFF;
uint64_t old = 0;
uint64_t new = 0;

static uint8_t check_variables(void);
static void update_variables(uint8_t tid);

static uint8_t check_variables(void) {
  // If only one visitor enters the critical section at any given time this
  // invariant will evaluate to true
  return new == (old + last_visitor);
}

static void update_variables(uint8_t tid) {
  old = new;
  new = old + tid;
  last_visitor = tid;
}

int main(void) {
  uint8_t tid = get_thread_attributes_cpu_id_from_smode();
  if (tid > 3) {
    return DIAG_FAILED;
  }

  for (uint8_t i = 0; i < NUM_ITER; i++) {
    acquire_lock(&lock);

    if (last_visitor != 0xFF && !check_variables()) {
      return DIAG_FAILED;
    }

    update_variables(tid);
    release_lock(&lock);
  }

  sync_all_cpus_from_smode();

  // Check final value
  if (new != NUM_ITER * (0 + 1 + 2 + 3)) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
