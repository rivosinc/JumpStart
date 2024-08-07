// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

int main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0xD0020000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_hart_id_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (SATP_MODE != VM_1_10_SV48) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  if (get_field(read_csr(satp), SATP64_MODE) != VM_1_10_SV48) {
    return DIAG_FAILED;
  }

  disable_mmu_from_smode();

  return DIAG_PASSED;
}
