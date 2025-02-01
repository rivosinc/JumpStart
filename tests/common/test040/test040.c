/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

void mmode_illegal_instruction_handler(void);
int mmode_illegal_instruction_function(void);

int mmode_main(void);
int main(void);

int an_smode_function(void);

void mmode_illegal_instruction_handler(void) {
  if (run_function_in_smode((uint64_t)an_smode_function) != 0xabcd) {
    jumpstart_mmode_fail();
  }

  if (get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode() !=
      MAX_NUM_CONTEXT_SAVES - 1) {
    jumpstart_mmode_fail();
  }

  // skip over the illegal instruction
  set_mepc_for_current_exception(get_mepc_for_current_exception() + 4);
}

int mmode_main(void) {
  if (MAX_NUM_CONTEXT_SAVES < 3) {
    // We need at least 3 mmode context saves to run the
    // mmode_illegal_instruction_function() function in this test.
    // 1. save mmode context to handle illegal instruction
    //   2. save mmode context before jumping to smode function from handler.
    //     3. ecall at the end of the smode function to return to mmode.
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  register_mmode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST, (uint64_t)(&mmode_illegal_instruction_handler));

  if (run_function_in_smode((uint64_t)an_smode_function) != 0xabcd) {
    return DIAG_FAILED;
  }

  if (mmode_illegal_instruction_function() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_mmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST);

  if (get_mmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST) != 0x0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode() !=
      MAX_NUM_CONTEXT_SAVES) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
