// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

int main(void) {
  for (int i = 0; i < 10; ++i) {
    sync_all_harts_from_smode();
  }

  return DIAG_PASSED;
}
