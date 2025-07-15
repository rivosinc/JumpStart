/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

extern uint64_t s_stage_pagetables_start;

int main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0xD0020000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_cpu_id_from_smode() != 0) {
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

  uint64_t satp_value = read_csr(satp);

  if (get_field(satp_value, SATP64_MODE) != VM_1_10_SV39) {
    return DIAG_FAILED;
  }

  uint64_t expected_satp_ppn =
      ((uint64_t)&s_stage_pagetables_start) >> PAGE_OFFSET;
  if (get_field(satp_value, SATP64_PPN) != expected_satp_ppn) {
    return DIAG_FAILED;
  }

  disable_mmu_from_smode();

  return DIAG_PASSED;
}
