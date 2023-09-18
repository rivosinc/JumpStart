// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

void test017_illegal_instruction_handler(void);
int test017_illegal_instruction_function(void);

int test016_main(void);
void main(void);

int test016_main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0x80020000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_hart_id_from_machine_mode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_machine_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_machine_mode() !=
      MACHINE_MODE_ENCODING) {
    return DIAG_FAILED;
  }

  register_machine_mode_trap_handler_override(
      MCAUSE_EC_ILLEGAL_INSTRUCTION,
      (uint64_t)(&test017_illegal_instruction_handler));

  if (test017_illegal_instruction_function() != 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
