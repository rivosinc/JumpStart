/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

void test003_illegal_instruction_handler(void);
int test003_illegal_instruction_function(void);
int alt_test003_illegal_instruction_function(void);

// Nest as many exceptions as are allowed.
uint8_t num_context_saves_to_take = MAX_NUM_CONTEXT_SAVES;

void test003_illegal_instruction_handler(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_smode_fail();
  }

  --num_context_saves_to_take;

  if (num_context_saves_to_take !=
      get_thread_attributes_num_context_saves_remaining_in_smode_from_smode()) {
    jumpstart_smode_fail();
  }

  if (num_context_saves_to_take > 0) {
    if (num_context_saves_to_take % 2) {
      if (alt_test003_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_smode_fail();
      }
    } else {
      if (test003_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_smode_fail();
      }
    }
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_smode_fail();
  }

  set_sepc_for_current_exception(get_sepc_for_current_exception() + 4);
}

int main(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

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
