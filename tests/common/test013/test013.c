/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

int main(void) {
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();
  if (cpu_id > 3) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (SATP_MODE != VM_1_10_SV39) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  if (get_field(read_csr(satp), SATP64_MODE) != VM_1_10_SV39) {
    return DIAG_FAILED;
  }

  disable_mmu_from_smode();

  return DIAG_PASSED;
}
