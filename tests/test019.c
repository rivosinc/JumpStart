// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  for (int i = 0; i < 10; ++i) {
    sync_all_harts_from_supervisor_mode();
  }

  return DIAG_PASSED;
}
