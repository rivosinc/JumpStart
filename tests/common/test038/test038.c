// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "heap.smode.h"
#include "jumpstart.h"

// We have smode init code that has to be run by one of the harts.
// This test has the non-primary hart run smode code after starting in mmode
// to make sure that the initialization is done irrespective of which core
// runs the smode code.

extern volatile uint8_t non_primary_hart_done;

uint8_t asm_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                      uint8_t a3, uint8_t a4, uint8_t a5,
                                      uint8_t a6);

uint8_t c_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                    uint8_t a3, uint8_t a4, uint8_t a5,
                                    uint8_t a6)
    __attribute__((section(".text.smode"))) __attribute__((const));

int call_malloc(void) __attribute__((section(".text.smode")));

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

int call_malloc(void) {
#define MAGIC_VALUE8 0xca
  uint8_t *x8 = malloc(sizeof(uint8_t));
  if (x8 == 0) {
    return 1;
  }

  *x8 = MAGIC_VALUE8;
  if (*x8 != MAGIC_VALUE8) {
    return 1;
  }

  return 0;
}

static int test_run_function_in_smode(void) {
  if (run_function_in_smode((uint64_t)asm_check_passed_in_arguments, 1, 2, 3, 4,
                            5, 6, 7) != DIAG_PASSED) {
    return 1;
  }

  // smode setup should have been done now.
  if (get_thread_attributes_smode_setup_done_from_mmode() != 1) {
    return 1;
  }

  if (run_function_in_smode((uint64_t)c_check_passed_in_arguments, 1, 2, 3, 4,
                            5, 6, 7) != DIAG_PASSED) {
    return 1;
  }

  if (run_function_in_smode((uint64_t)call_malloc) != 0) {
    return 1;
  }

  return 0;
}

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_mmode();
  if (hart_id > 1) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_mmode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  if (hart_id != PRIMARY_HART_ID) {
    // We haven't run any smode code so the smode setup should not be done.
    if (get_thread_attributes_smode_setup_done_from_mmode() != 0) {
      return DIAG_FAILED;
    }

    if (test_run_function_in_smode() == 1) {
      return DIAG_FAILED;
    }

    non_primary_hart_done = 1;
  } else {
    while (non_primary_hart_done == 0) {
      // Wait for the non-primary hart to finish.
    }

    // We haven't run any smode code so the smode setup should not be done.
    if (get_thread_attributes_smode_setup_done_from_mmode() != 0) {
      return DIAG_FAILED;
    }

    if (test_run_function_in_smode() == 1) {
      return DIAG_FAILED;
    }
  }

  return DIAG_PASSED;
}
