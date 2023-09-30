// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"
#include "tablewalk_functions.supervisor.h"

int main(void) {
  if ((read_csr(satp) >> SATP_MODE_LSB) != SATP_MODE_SV39) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;

  translate_VA(0x80021000, &xlate_info);

  // the valid bit is not set for the leaf PTE so the translation
  // will be marked unsuccessful.
  if (xlate_info.walk_successful != 0) {
    return DIAG_FAILED;
  }

  if (xlate_info.satp_mode != SATP_MODE_SV39) {
    return DIAG_FAILED;
  }

  if (xlate_info.levels_traversed != 3) {
    return DIAG_FAILED;
  }

  for (int i = 0; i < xlate_info.levels_traversed; i++) {
    if (*((uint64_t *)xlate_info.pte_address[i]) != xlate_info.pte_value[i]) {
      return DIAG_FAILED;
    }
  }

  if (xlate_info.pte_value[2] & PTE_VALID_BIT_MASK) {
    return DIAG_FAILED;
  }

  // Mark the leaf PTE as valid and retry the translation.
  *((uint64_t *)xlate_info.pte_address[2]) =
      xlate_info.pte_value[2] | PTE_VALID_BIT_MASK;
  asm volatile("sfence.vma");

  translate_VA(0x80021000, &xlate_info);
  if (xlate_info.walk_successful != 1) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
