// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  if (get_thread_attributes_hart_id_in_machine_mode() != 0) {
    return 1;
  }

  if (get_thread_attributes_bookend_magic_number_in_machine_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return 1;
  }

  if (get_thread_attributes_current_mode_in_machine_mode() !=
      MACHINE_MODE_ENCODING) {
    return 1;
  }

  return 0;
}
