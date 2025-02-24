/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"
#include "tablewalk.smode.h"

int main(void) {
  if (get_field(read_csr(satp), SATP64_MODE) != VM_1_10_SV39) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;

  translate_VA(0xC0021000, &xlate_info);

  // the valid bit is not set for the leaf PTE so the translation
  // will be marked unsuccessful.
  if (xlate_info.walk_successful != 0) {
    return DIAG_FAILED;
  }

  if (xlate_info.satp_mode != VM_1_10_SV39) {
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

  if (xlate_info.pte_value[2] & PTE_V) {
    return DIAG_FAILED;
  }

  // Mark the leaf PTE as valid and retry the translation.
  *((uint64_t *)xlate_info.pte_address[2]) = xlate_info.pte_value[2] | PTE_V;
  asm volatile("sfence.vma");

  translate_VA(0xC0021000, &xlate_info);
  if (xlate_info.walk_successful != 1) {
    return DIAG_FAILED;
  }

  if (xlate_info.pa != 0xC0021000) {
    return DIAG_FAILED;
  }

  translate_VA(0xC0022000, &xlate_info);
  if (xlate_info.walk_successful != 1) {
    return DIAG_FAILED;
  }
  if (xlate_info.pbmt_mode != PTE_PBMT_IO) {
    return DIAG_FAILED;
  }

  translate_VA(0xC0023000, &xlate_info);
  if (xlate_info.walk_successful != 1) {
    return DIAG_FAILED;
  }
  if (xlate_info.pbmt_mode != PTE_PBMT_NC) {
    return DIAG_FAILED;
  }

  // The default PBMT mode is PMA if not specified.
  translate_VA(0xC0024000, &xlate_info);
  if (xlate_info.walk_successful != 1) {
    return DIAG_FAILED;
  }
  if (xlate_info.pbmt_mode != PTE_PBMT_PMA) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
