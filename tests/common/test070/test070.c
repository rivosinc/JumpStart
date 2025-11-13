/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdbool.h>
#include <string.h>

#include "jumpstart.h"
#include "uart.smode.h"

extern uint64_t _EXPANDABLE_SC1_START;
extern uint64_t _EXPANDABLE_SC2_START;
extern uint64_t _FIXED_SC1_START;
extern uint64_t _EXPANDABLE_SC1_END;
extern uint64_t _EXPANDABLE_SC2_END;
extern uint64_t _FIXED_SC1_END;

#define EXPANDABLE_SC1_PAGE_SIZE 0x1000UL
#define EXPANDABLE_SC2_PAGE_SIZE 0x200000UL
#define FIXED_SC1_PAGE_SIZE      0x1000UL
#define EXPANDABLE_SC1_NUM_PAGES 1
#define EXPANDABLE_SC2_NUM_PAGES 2
#define FIXED_SC1_NUM_PAGES      1

#ifdef __clang__
__attribute__((optnone))
#else
__attribute__((optimize("O0")))
#endif
int main(void) {
  uint8_t cpuid = get_thread_attributes_cpu_id_from_smode();

  if (cpuid == PRIMARY_CPU_ID) {
    uint8_t num_cpus = MAX_NUM_CPUS_SUPPORTED;

    // Calculate sizes using linker variables
    uint64_t expandable_sc1_size =
        ((uint64_t)&_EXPANDABLE_SC1_END - (uint64_t)&_EXPANDABLE_SC1_START + 1);
    uint64_t expandable_sc2_size =
        ((uint64_t)&_EXPANDABLE_SC2_END - (uint64_t)&_EXPANDABLE_SC2_START + 1);
    uint64_t fixed_sc1_size =
        ((uint64_t)&_FIXED_SC1_END - (uint64_t)&_FIXED_SC1_START + 1);
    uint64_t expected_sc1_size =
        (EXPANDABLE_SC1_PAGE_SIZE * EXPANDABLE_SC1_NUM_PAGES * num_cpus);
    uint64_t expected_sc2_size =
        (EXPANDABLE_SC2_PAGE_SIZE * EXPANDABLE_SC2_NUM_PAGES * num_cpus);
    uint64_t expected_fixed_size = (FIXED_SC1_PAGE_SIZE * FIXED_SC1_NUM_PAGES);

    // Compare against expected sizes
    if (expandable_sc1_size != expected_sc1_size) {
      printk("Expandable SC1 size mismatch, Expected: %lu, Actual: %lu\n",
             expected_sc1_size, expandable_sc1_size);
      return DIAG_FAILED;
    }
    if (expandable_sc2_size != expected_sc2_size) {
      printk("Expandable SC2 size mismatch, Expected: %lu, Actual: %lu\n",
             expected_sc2_size, expandable_sc2_size);
      return DIAG_FAILED;
    }
    if (fixed_sc1_size != expected_fixed_size) {
      printk("Fixed SC1 size mismatch, Expected: %lu, Actual: %lu\n",
             expected_fixed_size, fixed_sc1_size);
      return DIAG_FAILED;
    }
  }
  return DIAG_PASSED;
}
