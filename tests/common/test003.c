// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

void test003_illegal_instruction_handler(void);
void test003_illegal_instruction_function(void);

int main(void) {

  register_supervisor_mode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test003_illegal_instruction_handler));

  test003_illegal_instruction_function();

  return DIAG_PASSED;
}
