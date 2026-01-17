/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"

// Separate sync points for each CPU combination
static uint32_t all_cpus_sync_point __attribute__((section(".data"))) = 0;
static uint32_t pair_01_sync_point __attribute__((section(".data"))) = 0;
static uint32_t pair_13_sync_point __attribute__((section(".data"))) = 0;
static uint32_t subset_012_sync_point __attribute__((section(".data"))) = 0;

int main(void) {
  // Get current CPU ID
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();

  // Test 1: Original sync_all_cpus_from_smode() test
  for (int i = 0; i < 5; ++i) {
    sync_all_cpus_from_smode();
  }

  if (ACTIVE_CPU_MASK != 0xf) {
    // We expect that all 4 cpus are active.
    return DIAG_FAILED;
  }

  // Test 2: sync_cpus_in_mask_from_smode() with all CPUs (should be equivalent
  // to sync_all_cpus_from_smode)
  for (int i = 0; i < 3; ++i) {
    sync_cpus_in_mask_from_smode(ACTIVE_CPU_MASK,
                                 (uint64_t)&all_cpus_sync_point);
  }

  // Test 3: sync_cpus_in_mask_from_smode() with individual CPUs
  // Each CPU syncs with itself only
  uint64_t single_cpu_mask = 1UL << cpu_id; // Only this CPU
  uint32_t single_cpu_sync_point = 0;

  for (int i = 0; i < 2; ++i) {
    sync_cpus_in_mask_from_smode(single_cpu_mask,
                                 (uint64_t)&single_cpu_sync_point);
  }

  // Test 4: sync_cpus_in_mask_from_smode() with pairs of CPUs
  // CPU 0 and 1 sync together
  if (cpu_id == 0 || cpu_id == 1) {
    uint64_t pair_mask = 0x3; // 0b0011 - CPUs 0 and 1

    for (int i = 0; i < 2; ++i) {
      sync_cpus_in_mask_from_smode(pair_mask, (uint64_t)&pair_01_sync_point);
    }
  }

  // Test 5: sync_cpus_in_mask_from_smode() with CPUs 1 and 3
  if (cpu_id == 1 || cpu_id == 3) {
    uint64_t pair_mask = 0xA; // 0b1010 - CPUs 1 and 3

    for (int i = 0; i < 2; ++i) {
      sync_cpus_in_mask_from_smode(pair_mask, (uint64_t)&pair_13_sync_point);
    }
  }

  // Test 6: sync_cpus_in_mask_from_smode() with subset (CPUs 0, 1, 2)
  if (cpu_id <= 2) {
    uint64_t subset_mask = 0x7; // 0b0111 - CPUs 0, 1, 2

    for (int i = 0; i < 2; ++i) {
      sync_cpus_in_mask_from_smode(subset_mask,
                                   (uint64_t)&subset_012_sync_point);
    }
  }

  return DIAG_PASSED;
}
