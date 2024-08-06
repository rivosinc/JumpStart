// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

void test046_illegal_instruction_handler(void)
    __attribute__((section(".text.vsmode")));
int test046_illegal_instruction_function(void)
    __attribute__((section(".text.vsmode")));
int alt_test046_illegal_instruction_function(void)
    __attribute__((section(".text.vsmode")));
int vsmode_main(void) __attribute__((section(".text.vsmode")));

// Nest as many exceptions as are allowed.
// We have saved the smode context to jump into vsmode so we have
// 1 less context save to take.
uint8_t num_context_saves_to_take = MAX_NUM_CONTEXT_SAVES - 1;

void test046_illegal_instruction_handler(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_vsmode_fail();
  }
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  --num_context_saves_to_take;

  if (num_context_saves_to_take !=
      get_thread_attributes_num_context_saves_remaining_in_smode_from_smode()) {
    jumpstart_vsmode_fail();
  }

  if (num_context_saves_to_take > 0) {
    if (num_context_saves_to_take % 2) {
      if (alt_test046_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_vsmode_fail();
      }
    } else {
      if (test046_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_vsmode_fail();
      }
    }
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_vsmode_fail();
  }
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  set_sepc_for_current_exception(get_sepc_for_current_exception() + 4);
}

int vsmode_main() {
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    return DIAG_FAILED;
  }

  register_vsmode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test046_illegal_instruction_handler));

  if (test046_illegal_instruction_function() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_vsmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST);

  if (get_vsmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST) != 0x0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}

int main(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }
  if (get_thread_attributes_current_v_bit_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (num_context_saves_to_take < 2) {
    // We test 2 different types of illegal instruction functions
    // and require at least 2 levels of nesting to test both.
    return DIAG_FAILED;
  }

  if (run_function_in_vsmode((uint64_t)vsmode_main) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_v_bit_from_smode() != 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
