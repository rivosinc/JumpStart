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

  if (get_thread_current_mode() != MSTATUS_MPP_MACHINE_MODE) {
    return 1;
  }

  setup_mmu_for_supervisor_mode();

  for (int i = 0; i < 10; ++i) {
    jump_to_supervisor_mode();
    if (get_thread_current_mode() != MSTATUS_MPP_SUPERVISOR_MODE) {
      return 1;
    }

    jump_to_machine_mode();
    if (get_thread_current_mode() != MSTATUS_MPP_MACHINE_MODE) {
      return 1;
    }
  }

  disable_mmu_for_supervisor_mode();

  return 0;
}
