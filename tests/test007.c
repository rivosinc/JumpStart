// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"
#include "jumpstart_uart.h"

int main(void) {
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

  setup_uart();
  puts("Hello World\n");
  printk("Checking format specifier int %d, char %c \n", 0xc001, 'A');

  return 0;
}
