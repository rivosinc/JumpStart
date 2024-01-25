// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

void test017_illegal_instruction_handler(void);
int test017_illegal_instruction_function(void);

int test016_main(void);
void main(void);

int test016_main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0xC0020000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_hart_id_from_mmode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_mmode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  register_mmode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test017_illegal_instruction_handler));

  if (test017_illegal_instruction_function() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_mmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST);

  if (get_mmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST) != 0x0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
