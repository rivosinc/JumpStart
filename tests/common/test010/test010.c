/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
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

extern uint64_t _TEXT_START;
extern uint64_t _TEXT_END;

extern uint64_t _DATA_START;
extern uint64_t _DATA_END;

#define ADDR(var) ((uint64_t)&(var))
#define VAR_WITHIN_REGION(var, start, end)                                     \
  (((ADDR(var) >= (start)) && (ADDR(var) + (sizeof(var)) < (end))) ? 1 : 0)

uint64_t uninitialized_var;
uint64_t zero_initialized_var = 0;

#define NUM_ARRAY_ELEMENTS 128
uint8_t uninitialized_arr[NUM_ARRAY_ELEMENTS];
uint8_t zero_initialized_arr[NUM_ARRAY_ELEMENTS] = {0};

__attribute__((section(".data"))) uint8_t store_faulted = 0;

static void skip_faulting_store_instruction(void) {
  volatile uint64_t data_start_address = ADDR(_DATA_START);
  volatile uint64_t expected_fault_address = data_start_address + 0x1000;

  uint64_t stval_value = read_csr(stval);
  if (stval_value != expected_fault_address) {
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

  // The compiler seems to optimize out the variables without volatile.
  volatile uint64_t text_start_address = ADDR(_TEXT_START);
  volatile uint64_t text_end_address = ADDR(_TEXT_END);

  // Check that these functions are in the right place.
  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != text_start_address) {
    return DIAG_FAILED;
  }

  // Check that the skip_faulting_store_instruction() is in the .text section.
  if (VAR_WITHIN_REGION(skip_faulting_store_instruction, text_start_address,
                        text_end_address) == 0) {
    return DIAG_FAILED;
  }

  // Check BSS.
  volatile uint64_t bss_start_address = ADDR(_BSS_START);
  volatile uint64_t bss_end_address = ADDR(_BSS_END);
  // These variables should be located within the BSS section.
  if (VAR_WITHIN_REGION(uninitialized_var, bss_start_address,
                        bss_end_address) == 0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(zero_initialized_var, bss_start_address,
                        bss_end_address) == 0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(uninitialized_arr, bss_start_address,
                        bss_end_address) == 0) {
    return DIAG_FAILED;
  }

  if (VAR_WITHIN_REGION(zero_initialized_arr, bss_start_address,
                        bss_end_address) == 0) {
    return DIAG_FAILED;
  }

  // All variables in the BSS should be initialized to zero.
  if (uninitialized_var || zero_initialized_var) {
    return DIAG_FAILED;
  }

  for (uint8_t i = 0; i < NUM_ARRAY_ELEMENTS; i++) {
    if (uninitialized_arr[i] || zero_initialized_arr[i]) {
      return DIAG_FAILED;
    }
  }

  volatile uint64_t data_start_address = ADDR(_DATA_START);
  volatile uint64_t data_end_address = ADDR(_DATA_END);
  // We have 2 pages in the .data section. There is an unmapped page in between
  // the 2 pages so there are 3 pages between _DATA_START and _DATA_END.
  // Check that there are 3 4K pages between _DATA_START and _DATA_END.
  if ((data_end_address - data_start_address + 1) != (3 * 0x1000)) {
    return DIAG_FAILED;
  }

  // RW to the first page.
  volatile uint64_t first_page_address = data_start_address;
  volatile uint64_t second_page_address = data_start_address + 0x1000;
  volatile uint64_t third_page_address = data_start_address + 0x2000;
  *((uint64_t *)first_page_address) = UINT64_C(0x1234567890ABCDEF);
  if (*((uint64_t *)first_page_address) != UINT64_C(0x1234567890ABCDEF)) {
    return DIAG_FAILED;
  }

  // RW to the third page.
  *((uint64_t *)third_page_address) = UINT64_C(0x1234567890ABCDEF);
  if (*((uint64_t *)third_page_address) != UINT64_C(0x1234567890ABCDEF)) {
    return DIAG_FAILED;
  }

  register_smode_trap_handler_override(
      RISCV_EXCP_STORE_PAGE_FAULT,
      (uint64_t)(&skip_faulting_store_instruction));

  // The second page doesn't have a mapping set up so it should fault.
  *((uint64_t *)second_page_address) = UINT64_C(0x1234567890ABCDEF);

  if (store_faulted == 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
