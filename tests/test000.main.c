// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

int main(void) {
  int hart_id = get_hart_id();
  if (hart_id != 0) {
    return 1;
  }

  return 0;
}
