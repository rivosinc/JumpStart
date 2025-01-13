// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "heap.smode.h"
#include "jumpstart.h"

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_smode();

  if (hart_id != 1 && hart_id != 3) {
    return DIAG_FAILED;
  }

  if (PRIMARY_HART_ID != 1) {
    // The hart with the lowest hart_id in the active hart mask is the primary
    // hart.
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
