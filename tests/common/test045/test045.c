// SPDX-FileCopyrightText: 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

// vsmode mode functions
// The assembly functions are already tagged with the .text.vsmode section
// attribute.
uint8_t asm_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                      uint8_t a3, uint8_t a4, uint8_t a5,
                                      uint8_t a6);
uint8_t c_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                    uint8_t a3, uint8_t a4, uint8_t a5,
                                    uint8_t a6)
    __attribute__((section(".text.vsmode"))) __attribute__((const));

uint8_t c_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                    uint8_t a3, uint8_t a4, uint8_t a5,
                                    uint8_t a6) {
  if (a0 != 1) {
    return DIAG_FAILED;
  }
  if (a1 != 2) {
    return DIAG_FAILED;
  }
  if (a2 != 3) {
    return DIAG_FAILED;
  }
  if (a3 != 4) {
    return DIAG_FAILED;
  }
  if (a4 != 5) {
    return DIAG_FAILED;
  }
  if (a5 != 6) {
    return DIAG_FAILED;
  }
  if (a6 != 7) {
    return DIAG_FAILED;
  }
  return DIAG_PASSED;
}

int main(void) {
  if (get_thread_attributes_hart_id_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  if (run_function_in_vsmode((uint64_t)asm_check_passed_in_arguments, 1, 2, 3,
                             4, 5, 6, 7) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  if (run_function_in_vsmode((uint64_t)c_check_passed_in_arguments, 1, 2, 3, 4,
                             5, 6, 7) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
