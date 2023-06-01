// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  if (get_thread_hart_id() != 0) {
    return 1;
  }

  if (get_thread_bookend_magic_number() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return 1;
  }

  if (get_diag_satp_mode() != SATP_MODE_SV39) {
    return 1;
  }

  if (get_thread_current_mode() != MSTATUS_MPP_SUPERVISOR_MODE) {
    return 1;
  }

  setup_mmu_for_supervisor_mode();

  disable_mmu_for_supervisor_mode();

  return 0;
}
