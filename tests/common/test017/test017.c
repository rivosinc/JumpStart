// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

void test017_illegal_instruction_handler(void);
int test017_illegal_instruction_function(void);
int alt_test017_illegal_instruction_function(void);

int test017_main(void);
int main(void);

// Nest as many exceptions as are allowed.
uint8_t num_context_saves_to_take = MAX_NUM_CONTEXT_SAVES;

void test017_illegal_instruction_handler(void) {
  --num_context_saves_to_take;

  // We just took an exception from mmode to mmode so the mstatus.MPP bit
  // should be set to PRV_M.
  if (get_thread_attributes_current_mode_from_mmode() != PRV_M ||
      (((read_csr(mstatus) >> MSTATUS_MPP_SHIFT) & 0x3) != PRV_M)) {
    jumpstart_mmode_fail();
  }

  if (num_context_saves_to_take !=
      get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode()) {
    jumpstart_mmode_fail();
  }

  if (num_context_saves_to_take > 0) {
    if (num_context_saves_to_take % 2) {
      if (alt_test017_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_mmode_fail();
      }
    } else {
      if (test017_illegal_instruction_function() != DIAG_PASSED) {
        jumpstart_mmode_fail();
      }
    }
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    jumpstart_mmode_fail();
  }

  set_mepc_for_current_exception(get_mepc_for_current_exception() + 4);
}

int test017_main(void) {
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

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
