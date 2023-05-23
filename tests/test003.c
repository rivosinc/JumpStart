// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

void test003_illegal_instruction_handler(void);
void test003_illegal_instruction_function(void);

int main(void) {

  register_trap_handler_override(
      MSTATUS_MPP_MACHINE_MODE, MCAUSE_EC_ILLEGAL_INSTRUCTION,
      (uint64_t)(&test003_illegal_instruction_handler));

  test003_illegal_instruction_function();

  return 0;
}
