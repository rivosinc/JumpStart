/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

#define __vs_text __attribute__((section(".text.vsmode")))
#define __vs_data __attribute__((section(".data.vsmode")))

void test046_illegal_instruction_handler(void) __vs_text;
int test046_illegal_instruction_function(void) __vs_text;
int alt_test046_illegal_instruction_function(void) __vs_text;
int vsmode_main(void) __vs_text;

// Nest as many exceptions as are allowed.
// We have saved the smode context to jump into vsmode so we have
// 1 less context save to take.
uint8_t __vs_data num_context_saves_to_take[MAX_NUM_HARTS_SUPPORTED] = {
    [0 ... MAX_NUM_HARTS_SUPPORTED - 1] = MAX_NUM_CONTEXT_SAVES - 1};

void test046_illegal_instruction_handler(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_smode();

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_vsmode_fail();
  }
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  --num_context_saves_to_take[hart_id];

  if (num_context_saves_to_take[hart_id] !=
      get_thread_attributes_num_context_saves_remaining_in_smode_from_smode()) {
    jumpstart_vsmode_fail();
  }

  if (num_context_saves_to_take[hart_id] > 0) {
    if (num_context_saves_to_take[hart_id] % 2) {
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
  uint64_t hart_id = get_thread_attributes_hart_id_from_smode();

  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    return DIAG_FAILED;
  }

  register_vsmode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST,
      (uint64_t)(&test046_illegal_instruction_handler));

  if (num_context_saves_to_take[hart_id] < 2) {
    // We test 2 different types of illegal instruction functions
    // and require at least 2 levels of nesting to test both.
    return DIAG_FAILED;
  }

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

  if (run_function_in_vsmode((uint64_t)vsmode_main) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_v_bit_from_smode() != 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
