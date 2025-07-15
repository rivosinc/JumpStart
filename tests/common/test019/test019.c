/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart.h"

int main(void) {
  for (int i = 0; i < 10; ++i) {
    sync_all_cpus_from_smode();
  }

  return DIAG_PASSED;
}
