// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

void test003_illegal_instruction_handler(void);
int test003_illegal_instruction_function(void);

int main(void) {

  register_supervisor_mode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test003_illegal_instruction_handler));

  if (test003_illegal_instruction_function() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_supervisor_mode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST);

  if (get_supervisor_mode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST) !=
      0x0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
