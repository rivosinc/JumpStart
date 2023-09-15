// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"
#include "uart_functions.supervisor.h"

int main(void) {
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

  /* TODO: We don't have a spinlock. Allow only Hart0 to write to the UART */
  uint8_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();
  if (hart_id == 0) {
    puts("Hello World\n");
    printk("Checking format specifier int %d, char %c \n", 0xc001, 'A');
  } else if (hart_id > 3) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
