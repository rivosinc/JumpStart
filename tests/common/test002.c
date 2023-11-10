// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

// user mode functions
// The assembly functions are already tagged with the .text.user section
// attribute.
uint8_t get_bytes_to_copy(void);
int copy_bytes(void);
int compare_copied_bytes(void) __attribute__((section(".text.user")))
__attribute__((pure));

extern uint64_t source_location;
extern uint64_t destination_location;

int main(void) {
  if (get_thread_attributes_hart_id_from_supervisor_mode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_supervisor_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_supervisor_mode() != PRV_S) {
    return DIAG_FAILED;
  }

  int bytes_to_copy = run_function_in_user_mode((uint64_t)get_bytes_to_copy, 0);
  if (bytes_to_copy != 512) {
    return DIAG_FAILED;
  }

  // We want supervisor mode to be able to write to the user mode data area
  // so set SSTATUS.SUM to 1.
  uint64_t sstatus_value = read_csr(sstatus);
  sstatus_value |= MSTATUS_SUM;
  write_csr(sstatus, sstatus_value);

  uint64_t fill_value = 0x123456789abcdef0;

  for (uint8_t i = 0; i < 5; ++i) {
    // Read a Supervisor mode register to really make sure we're in supervisor
    // mode.
    fill_value += read_csr(sscratch);

    uint64_t *src = (uint64_t *)&source_location;
    for (int j = 0; j < (bytes_to_copy / 8); ++j) {
      src[j] = fill_value;
      ++fill_value;
    }

    if (run_function_in_user_mode((uint64_t)copy_bytes, 0) != 0) {
      return DIAG_FAILED;
    }

    if (get_thread_attributes_current_mode_from_supervisor_mode() != PRV_S) {
      return DIAG_FAILED;
    }

    if (run_function_in_user_mode((uint64_t)compare_copied_bytes, 0) != 0) {
      return DIAG_FAILED;
    }

    if (get_thread_attributes_current_mode_from_supervisor_mode() != PRV_S) {
      return DIAG_FAILED;
    }
  }

  return DIAG_PASSED;
}

int compare_copied_bytes(void) {
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
