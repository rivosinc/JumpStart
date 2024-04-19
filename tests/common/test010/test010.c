// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

extern uint64_t _JUMPSTART_TEXT_MMODE_INIT_ENTER_START;
extern uint64_t _JUMPSTART_TEXT_SMODE_INIT_ENTER_START;
extern uint64_t _JUMPSTART_TEXT_UMODE_START;
extern uint64_t _BSS_START;
extern uint64_t _BSS_END;

#define ADDR(var) ((uint64_t) & (var))
#define VAR_WITHIN_REGION(var, start, end)                                     \
  (((ADDR(var) >= (start)) && (ADDR(var) + (sizeof(var)) < (end))) ? 1 : 0)

uint64_t uninitialized_var;
uint64_t zero_initialized_var = 0;

uint8_t uninitialized_arr[128];
uint8_t zero_initialized_arr[128] = {0};

__attribute__((pure)) int main(void) {
  // Check that the M-mode, S-mode, U-mode start address overrides worked.
  uint64_t mmode_start_address =
      (uint64_t)&_JUMPSTART_TEXT_MMODE_INIT_ENTER_START;
  if (mmode_start_address != 0x81000000) {
    return DIAG_FAILED;
  }

  uint64_t smode_start_address =
      (uint64_t)&_JUMPSTART_TEXT_SMODE_INIT_ENTER_START;
  if (smode_start_address != 0x82000000) {
    return DIAG_FAILED;
  }

  uint64_t umode_start_address = (uint64_t)&_JUMPSTART_TEXT_UMODE_START;
  if (umode_start_address != 0x83000000) {
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

  return DIAG_PASSED;
}
