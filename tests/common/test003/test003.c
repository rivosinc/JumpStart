// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

void test003_illegal_instruction_handler(void);
int test003_illegal_instruction_function(void);

void test003_illegal_instruction_handler(void) {
  set_sepc_for_current_exception(get_sepc_for_current_exception() + 4);
}

int main(void) {

  register_smode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test003_illegal_instruction_handler));

  if (test003_illegal_instruction_function() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_smode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST);

  if (get_smode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST) != 0x0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
