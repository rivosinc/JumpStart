// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  if (get_thread_attributes_current_mode() != SUPERVISOR_MODE_ENCODING) {
    return 1;
  }
  setup_mmu_for_supervisor_mode();

  uint64_t new_sscratch_value = 0x123456789abcdef0;
  write_csr(sscratch, new_sscratch_value);

  if (read_csr(sscratch) != new_sscratch_value) {
    return 1;
  }

  disable_mmu_for_supervisor_mode();

  return 0;
}
