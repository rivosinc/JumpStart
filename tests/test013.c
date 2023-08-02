// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();
  if (hart_id > 3) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_supervisor_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_diag_satp_mode_from_supervisor_mode() != SATP_MODE_SV39) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_supervisor_mode() !=
      SUPERVISOR_MODE_ENCODING) {
    return DIAG_FAILED;
  }

  if ((read_csr(satp) >> SATP_MODE_LSB) != SATP_MODE_SV39) {
    return DIAG_FAILED;
  }

  disable_mmu_from_supervisor_mode();

  return DIAG_PASSED;
}
