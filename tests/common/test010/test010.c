/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

extern uint64_t _JUMPSTART_CPU_TEXT_MMODE_INIT_ENTER_START;
extern uint64_t _JUMPSTART_CPU_TEXT_SMODE_INIT_ENTER_START;
extern uint64_t _JUMPSTART_CPU_TEXT_UMODE_START;
extern uint64_t _BSS_START;
extern uint64_t _BSS_END;

#define ADDR(var) ((uint64_t) & (var))
#define VAR_WITHIN_REGION(var, start, end)                                     \
  (((ADDR(var) >= (start)) && (ADDR(var) + (sizeof(var)) < (end))) ? 1 : 0)

uint64_t uninitialized_var;
uint64_t zero_initialized_var = 0;

uint8_t uninitialized_arr[128];
uint8_t zero_initialized_arr[128] = {0};

uint8_t store_faulted = 0;

static void skip_faulting_store_instruction(void) {
  uint64_t stval_value = read_csr(stval);
  if (stval_value != 0xC0023000) {
    jumpstart_smode_fail();
  }

  uint64_t reg = get_sepc_for_current_exception();

  uint32_t opcode = *((uint32_t *)reg);
  uint8_t instruction_size = 2;
  if ((opcode & 0x3) == 0x3) {
    instruction_size = 4;
  }

  /* Just skip the faulting instruction and move to next instruction. */
  set_sepc_for_current_exception(reg + instruction_size);

  store_faulted = 1;
}

__attribute__((section(".text.startup"))) __attribute__((pure)) int main(void) {
  // Check that the M-mode, S-mode, U-mode start address overrides worked.
  uint64_t mmode_start_address =
      (uint64_t)&_JUMPSTART_CPU_TEXT_MMODE_INIT_ENTER_START;
  if (mmode_start_address != MMODE_START_ADDRESS) {
    return DIAG_FAILED;
  }

  uint64_t smode_start_address =
      (uint64_t)&_JUMPSTART_CPU_TEXT_SMODE_INIT_ENTER_START;
  if (smode_start_address != SMODE_START_ADDRESS) {
    return DIAG_FAILED;
  }

  uint64_t umode_start_address = (uint64_t)&_JUMPSTART_CPU_TEXT_UMODE_START;
  if (umode_start_address != UMODE_START_ADDRESS) {
    return DIAG_FAILED;
  }

  // Check that these functions are in the right place.
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0xC0020000) {
    return DIAG_FAILED;
  }

  // Check BSS.
  // These variables should be located within the BSS section.
  if (VAR_WITHIN_REGION(uninitialized_var, ADDR(_BSS_START), ADDR(_BSS_END)) ==
      0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(zero_initialized_var, ADDR(_BSS_START),
                        ADDR(_BSS_END)) == 0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(uninitialized_arr, ADDR(_BSS_START), ADDR(_BSS_END)) ==
      0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(zero_initialized_arr, ADDR(_BSS_START),
                        ADDR(_BSS_END)) == 0) {
    return DIAG_FAILED;
  }

  // All variables in the BSS should be initialized to zero.
  if (uninitialized_var || zero_initialized_var) {
    return DIAG_FAILED;
  }

  for (uint8_t i = 0; i < 128; i++) {
    if (uninitialized_arr[i] || zero_initialized_arr[i]) {
      return DIAG_FAILED;
    }
  }

  // Read and write to the page at 0xC0022000
  uint64_t *ptr = (uint64_t *)0xC0022000;
  *ptr = UINT64_C(0x1234567890ABCDEF);
  if (*ptr != UINT64_C(0x1234567890ABCDEF)) {
    return DIAG_FAILED;
  }

  // Read and write to the page at 0xC0024000
  ptr = (uint64_t *)0xC0024000;
  *ptr = UINT64_C(0x1234567890ABCDEF);
  if (*ptr != UINT64_C(0x1234567890ABCDEF)) {
    return DIAG_FAILED;
  }

  register_smode_trap_handler_override(
      RISCV_EXCP_STORE_PAGE_FAULT,
      (uint64_t)(&skip_faulting_store_instruction));

  // This page is also part of the .data linker script section but it does
  // not have a page mapping so it will fault.
  ptr = (uint64_t *)0xC0023000;
  *ptr = UINT64_C(0x1234567890ABCDEF);

  if (store_faulted == 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
