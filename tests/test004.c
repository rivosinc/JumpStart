// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

void hwp_ampm_diag(void);

int main(void) {
  setup_mmu_for_supervisor_mode();

  jump_to_supervisor_mode();

  hwp_ampm_diag();

  disable_mmu_for_supervisor_mode();

  return 0;
}
