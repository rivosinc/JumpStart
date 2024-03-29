// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

void just_nops(void);

int main(void) {
  if (get_thread_attributes_hart_id_from_mmode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_mmode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_mmode() != PRV_M) {
    return DIAG_FAILED;
  }

  just_nops();

  return DIAG_PASSED;
}
