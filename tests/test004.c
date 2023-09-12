// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

void hwp_ampm_diag(void);

int main(void) {
  hwp_ampm_diag();

  return DIAG_PASSED;
}
