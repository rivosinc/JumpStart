// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0x80000000) {
    return 1;
  }

  if (get_thread_attributes_hart_id_from_supervisor_mode() != 0) {
    return 1;
  }

  if (get_thread_attributes_bookend_magic_number_from_supervisor_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return 1;
  }

  if (get_diag_satp_mode_from_supervisor_mode() != SATP_MODE_SV39) {
    return 1;
  }

  if (get_thread_attributes_current_mode_from_supervisor_mode() !=
      SUPERVISOR_MODE_ENCODING) {
    return 1;
  }

  if ((read_csr(satp) >> SATP_MODE_LSB) != SATP_MODE_SV39) {
    return 1;
  }

  disable_mmu_from_supervisor_mode();

  return 0;
}
