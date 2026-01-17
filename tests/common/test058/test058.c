/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "heap.smode.h"
#include "jumpstart.h"

int main(void) {
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();

  if (cpu_id != 1 && cpu_id != 3) {
    return DIAG_FAILED;
  }

  if (PRIMARY_CPU_ID != 1) {
    // The cpu with the lowest cpu_id in the active cpu mask is the primary
    // cpu.
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
