// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"
#include "tablewalk_functions.smode.h"

extern uint64_t data_area;
extern uint64_t load_from_address(uint64_t address);

uint8_t PA_access_faulted = 0;

int main(void) {
  const uint64_t rw_VA_alias = UINT64_C(0xC0033000);
  const uint64_t ro_VA_alias = UINT64_C(0xC0053000);
  const uint64_t PA = UINT64_C(0xC0043000);
  uint64_t data_area_address = (uint64_t)&data_area;
  if (data_area_address != PA) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;

  translate_VA(rw_VA_alias, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != PA)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[2] & (PTE_W | PTE_R | PTE_X)) != (PTE_W | PTE_R)) {
    return DIAG_FAILED;
  }
  // The RW alias has 2 pages allocated.
  translate_VA(rw_VA_alias + 0x1000, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != (PA + 0x1000))) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[2] & (PTE_W | PTE_R | PTE_X)) != (PTE_W | PTE_R)) {
    return DIAG_FAILED;
  }

  translate_VA(ro_VA_alias, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != PA)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[2] & (PTE_W | PTE_R | PTE_X)) != PTE_R) {
    return DIAG_FAILED;
  }
  // The RO alias has only 1 page allocated.
  translate_VA(ro_VA_alias + 0x1000, &xlate_info);
  if ((xlate_info.walk_successful != 0)) {
    return DIAG_FAILED;
  }

  if (load_from_address(rw_VA_alias) != 0) {
    return DIAG_FAILED;
  }
  if (load_from_address(ro_VA_alias) != 0) {
    return DIAG_FAILED;
  }

  const uint64_t magic_value = 0xcafecafecafecafe;
  *(uint64_t *)rw_VA_alias = magic_value;

  if (load_from_address(rw_VA_alias) != magic_value) {
    return DIAG_FAILED;
  }
  if (load_from_address(ro_VA_alias) != magic_value) {
    return DIAG_FAILED;
  }

  disable_mmu_from_smode();

  // PA access should now succeed with the MMU off.
  uint64_t value_at_PA = load_from_address(PA);
  if (value_at_PA != magic_value) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
