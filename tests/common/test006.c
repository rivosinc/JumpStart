// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

int main(void) {
  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  uint64_t new_sscratch_value = 0x123456789abcdef0;
  write_csr(sscratch, new_sscratch_value);

  if (read_csr(sscratch) != new_sscratch_value) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
