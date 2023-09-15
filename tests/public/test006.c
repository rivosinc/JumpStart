// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

int main(void) {
  if (get_thread_attributes_current_mode_from_supervisor_mode() !=
      SUPERVISOR_MODE_ENCODING) {
    return DIAG_FAILED;
  }

  uint64_t new_sscratch_value = 0x123456789abcdef0;
  write_csr(sscratch, new_sscratch_value);

  if (read_csr(sscratch) != new_sscratch_value) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
