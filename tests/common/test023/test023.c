// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

// Supervisor functions
// The assembly functions are already tagged with the .text.smode section
// attribute.
int smode_illegal_instruction_function(void);
int smode_breakpoint_and_illegal_instruction_function(void)
    __attribute__((section(".text.smode")));
void smode_breakpoint_handler(void) __attribute__((section(".text.smode")));

static void mmode_illegal_instruction_handler(void) {
  set_mepc_for_current_exception(get_mepc_for_current_exception() + 4);
}

int main(void) {
  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  // Handle illegal instructions traps from smode in mmode.
  clear_csr(medeleg, 1 << RISCV_EXCP_ILLEGAL_INST);
  register_mmode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST, (uint64_t)(&mmode_illegal_instruction_handler));

  // Run an illegal instruction in smode that will be handled in mmode.
  int ret = run_function_in_smode((uint64_t)smode_illegal_instruction_function);
  if (ret != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // Run a ebreak instruction in smode that will be handled in smode.
  // The smode handler for the ebreak will run an illegal instruction which
  // will be handled in mmode. This tests nested trap handling.
  ret = run_function_in_smode(
      (uint64_t)smode_breakpoint_and_illegal_instruction_function);
  if (ret != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}

void smode_breakpoint_handler(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    jumpstart_smode_fail();
  }

  if (smode_illegal_instruction_function() != DIAG_PASSED) {
    jumpstart_smode_fail();
  }

  // Skip over the c.ebreak instruction
  set_sepc_for_current_exception(get_sepc_for_current_exception() + 2);
}

int smode_breakpoint_and_illegal_instruction_function(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  register_smode_trap_handler_override(RISCV_EXCP_BREAKPOINT,
                                       (uint64_t)(&smode_breakpoint_handler));

  asm volatile("c.ebreak");

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
