// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"
#include "tablewalk.smode.h"

extern uint64_t data_area;
extern uint64_t load_from_address(uint64_t address);

int main(void) {
  const uint64_t rw_VA_alias = UINT64_C(0xc0400000);
  const uint64_t ro_VA_alias = UINT64_C(0xc0800000);

  const uint64_t PA = UINT64_C(0xc0400000);
  const uint32_t region_size_in_bytes = 0x200000;
  uint64_t data_area_address = (uint64_t)&data_area;
  if (data_area_address != PA) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;

  translate_VA(rw_VA_alias, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != PA) ||
      (xlate_info.levels_traversed != 4)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[3] & (PTE_W | PTE_R | PTE_X)) != (PTE_W | PTE_R)) {
    return DIAG_FAILED;
  }

  // Check the last page in the region.
  translate_VA(rw_VA_alias + region_size_in_bytes - 1, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.levels_traversed != 4)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[3] & (PTE_W | PTE_R | PTE_X)) != (PTE_W | PTE_R)) {
    return DIAG_FAILED;
  }

  translate_VA(ro_VA_alias, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != PA) ||
      (xlate_info.levels_traversed != 4)) {
    return DIAG_FAILED;
  }
  // Check the last page in the region.
  translate_VA(ro_VA_alias + region_size_in_bytes - 1, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.levels_traversed != 4)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[3] & (PTE_W | PTE_R | PTE_X)) != (PTE_R)) {
    return DIAG_FAILED;
  }

  *(uint64_t *)rw_VA_alias = 0xcafecafecafecafe;
  *(uint64_t *)(rw_VA_alias + region_size_in_bytes - 8) = 0xdeaddeaddeaddead;

  // Using direct assembly loads helps us to avoid compiler optimization issues.
  if (load_from_address(ro_VA_alias) != 0xcafecafecafecafe) {
    return DIAG_FAILED;
  }
  if (load_from_address(ro_VA_alias + region_size_in_bytes - 8) !=
      0xdeaddeaddeaddead) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
