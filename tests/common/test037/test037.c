// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

float double_float32_number(float number);
void run_vector_instructions(void);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wfloat-equal"

int main(void) {
  if ((read_csr(sstatus) & SSTATUS_FS) == 0) {
    return DIAG_FAILED;
  }

  if (double_float32_number(1.0f) != 2.0f) {
    return DIAG_FAILED;
  }

  if (double_float32_number(3.5f) != 7.0f) {
    return DIAG_FAILED;
  }

  run_vector_instructions();

  return DIAG_PASSED;
}

#pragma GCC diagnostic pop
