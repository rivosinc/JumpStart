/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

int main(void) {
  if (get_thread_attributes_hart_id_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (SATP_MODE != VM_1_10_MBARE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  if (get_field(read_csr(satp), SATP64_MODE) != VM_1_10_MBARE) {
    return DIAG_FAILED;
  }

  if (get_field(read_csr(satp), SATP64_PPN) != 0) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
