// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int test_umode(void);

int main(void) {
  if (get_thread_attributes_hart_id() != 0) {
    return 1;
  }

  if (get_thread_attributes_bookend_magic_number() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return 1;
  }

  if (get_thread_attributes_current_mode() != SUPERVISOR_MODE_ENCODING) {
    return 1;
  }

  setup_mmu_for_supervisor_mode();

  if (run_function_in_user_mode(test_umode) != 0) {
    return 1;
  }

  if (get_thread_attributes_current_mode() != SUPERVISOR_MODE_ENCODING) {
    return 1;
  }

  disable_mmu_for_supervisor_mode();

  return 0;
}
