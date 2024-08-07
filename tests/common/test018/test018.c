// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

// Supervisor functions
// The assembly functions are already tagged with the .text.smode section
// attribute.
uint8_t asm_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                      uint8_t a3, uint8_t a4, uint8_t a5,
                                      uint8_t a6);
uint8_t c_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                    uint8_t a3, uint8_t a4, uint8_t a5,
                                    uint8_t a6)
    __attribute__((section(".text.smode"))) __attribute__((const));
uint8_t get_bytes_to_copy(void);
int copy_bytes(void);
int compare_copied_bytes(void) __attribute__((section(".text.smode")))
__attribute__((pure));

extern uint64_t source_location;
extern uint64_t destination_location;

uint8_t c_check_passed_in_arguments(uint8_t a0, uint8_t a1, uint8_t a2,
                                    uint8_t a3, uint8_t a4, uint8_t a5,
                                    uint8_t a6) {
  if (get_thread_attributes_num_context_saves_remaining_in_mmode_from_smode() !=
      MAX_NUM_CONTEXT_SAVES - 1) {
    // we should have consumed one of the mmode context saves to run
    // the smode function.
    return DIAG_FAILED;
  }

  if (get_thread_attributes_num_context_saves_remaining_in_smode_from_smode() !=
      MAX_NUM_CONTEXT_SAVES) {
    return DIAG_FAILED;
  }

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
  if (MAX_NUM_CONTEXT_SAVES < 2) {
    // We need at least 2 smode context saves to run
    // run_function_in_smode().
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

  // We haven't run any smode code so the smode setup should not be done.
  if (get_thread_attributes_smode_setup_done_from_mmode() != 0) {
    return DIAG_FAILED;
  }

  if (run_function_in_smode((uint64_t)asm_check_passed_in_arguments, 1, 2, 3, 4,
                            5, 6, 7) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // smode setup should have been done now.
  if (get_thread_attributes_smode_setup_done_from_mmode() != 1) {
    return DIAG_FAILED;
  }

  if (run_function_in_smode((uint64_t)c_check_passed_in_arguments, 1, 2, 3, 4,
                            5, 6, 7) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  int bytes_to_copy = run_function_in_smode((uint64_t)get_bytes_to_copy);
  if (bytes_to_copy != 512) {
    return DIAG_FAILED;
  }

  uint64_t fill_value = 0x123456789abcdef0;

  for (uint8_t i = 0; i < 5; ++i) {
    // Read a smode register to really make sure we're in supervisor
    // mode.
    fill_value += read_csr(sscratch);
    uint64_t *src = (uint64_t *)&source_location;
    for (uint8_t j = 0; j < (bytes_to_copy / 8); ++j) {
      src[j] = fill_value;
      ++fill_value;
    }

    if (run_function_in_smode((uint64_t)copy_bytes) != 0) {
      return DIAG_FAILED;
    }

    if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
      return DIAG_FAILED;
    }

    if (run_function_in_smode((uint64_t)compare_copied_bytes) != 0) {
      return DIAG_FAILED;
    }

    if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
      return DIAG_FAILED;
    }
  }

  if (get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode() !=
      MAX_NUM_CONTEXT_SAVES) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_num_context_saves_remaining_in_smode_from_mmode() !=
      MAX_NUM_CONTEXT_SAVES) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}

int compare_copied_bytes(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  uint8_t bytes_to_copy = get_bytes_to_copy();

  uint64_t *src = (uint64_t *)&source_location;
  uint64_t *dst = (uint64_t *)&destination_location;

  for (int i = 0; i < (bytes_to_copy / 8); i++) {
    if (src[i] != dst[i]) {
      return DIAG_FAILED;
    }
  }

  return DIAG_PASSED;
}
