// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_smode();
  if (hart_id == 2) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
