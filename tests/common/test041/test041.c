/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

// This is a copy of test003 with one extra nested exception that should
// cause this to fail.

#include "cpu_bits.h"
#include "jumpstart.h"

void illegal_instruction_handler(void);
int illegal_instruction_function(void);

// Take one more exception than is allowed so that we can fail gracefully.
uint8_t num_context_saves_to_take = MAX_NUM_CONTEXT_SAVES + 1;

void illegal_instruction_handler(void) {
  --num_context_saves_to_take;

  if (num_context_saves_to_take > 0) {
    illegal_instruction_function();
  }

  set_sepc_for_current_exception(get_sepc_for_current_exception() + 4);
}

int main(void) {
  register_smode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST, (uint64_t)(&illegal_instruction_handler));

  illegal_instruction_function();

  return DIAG_PASSED;
}
