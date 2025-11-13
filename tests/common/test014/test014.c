/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"

int main(void) {
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();
  if (cpu_id == 2) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
