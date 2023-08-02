// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();
  if (hart_id == 2) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
