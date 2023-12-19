// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"
#include "tablewalk_functions.supervisor.h"

#define SIZE_2M     0x200000
#define SIZE_1G     0x40000000
#define MAGIC_VALUE 0xcafecafecafecafe

uint64_t load_from_address(uint64_t address) __attribute__((pure));
int test_mapping(uint64_t VA, uint64_t PA, uint8_t expected_xwr,
                 uint64_t expected_read, uint64_t write_test_value);

uint64_t load_from_address(uint64_t address) {
  return *((uint64_t *)(address));
}

int test_mapping(uint64_t VA, uint64_t PA, uint8_t expected_xwr,
                 uint64_t expected_read, uint64_t write_test_value) {

  struct translation_info xlate_info;
  translate_VA(VA, &xlate_info);
  if ((xlate_info.walk_successful == 0) || (xlate_info.pa != PA)) {
    return DIAG_FAILED;
  }
  if ((xlate_info.pte_value[xlate_info.levels_traversed - 1] &
       (PTE_W | PTE_R | PTE_X)) != expected_xwr) {
    return DIAG_FAILED;
  }

  if (expected_xwr & PTE_R) {
    if (load_from_address(VA) != expected_read) {
      return DIAG_FAILED;
    }
  }
  if (expected_xwr & PTE_W) {
    *(uint64_t *)VA = write_test_value;
    if (load_from_address(VA) != write_test_value) {
      return DIAG_FAILED;
    }
  }

  return DIAG_PASSED;
}

int main(void) {
  if (test_mapping(UINT64_C(0xD0000000), UINT64_C(0xE0000000), (PTE_R | PTE_W),
                   0, 0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  if (test_mapping(UINT64_C(0xD0000000) + SIZE_2M,
                   UINT64_C(0xE0000000) + SIZE_2M, (PTE_R | PTE_W), 0,
                   0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  // Test write
  if (test_mapping(UINT64_C(0xD0000000), UINT64_C(0xE0000000), (PTE_R | PTE_W),
                   0, MAGIC_VALUE) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  // Test Alias
  if (test_mapping(UINT64_C(0xD0400000), UINT64_C(0xE0000000), (PTE_R),
                   MAGIC_VALUE, 0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }

  if (test_mapping(UINT64_C(0x100000000), UINT64_C(0x100000000),
                   (PTE_R | PTE_W), 0, 0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  if (test_mapping(UINT64_C(0x100000000) + SIZE_1G,
                   UINT64_C(0x100000000) + SIZE_1G, (PTE_R | PTE_W), 0,
                   0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  // Test write
  if (test_mapping(UINT64_C(0x100000000), UINT64_C(0x100000000),
                   (PTE_R | PTE_W), 0, MAGIC_VALUE) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  // Test Alias
  if (test_mapping(UINT64_C(0x180000000), UINT64_C(0x100000000), (PTE_R),
                   MAGIC_VALUE, 0) == DIAG_FAILED) {
    return DIAG_FAILED;
  }

  disable_mmu_from_supervisor_mode();

  // PA access should now succeed with the MMU off.
  uint64_t value_at_2M_PA = load_from_address(UINT64_C(0xE0000000));
  if (value_at_2M_PA != MAGIC_VALUE) {
    return DIAG_FAILED;
  }
  uint64_t value_at_1G_PA = load_from_address(UINT64_C(0x100000000));
  if (value_at_1G_PA != MAGIC_VALUE) {
    return DIAG_FAILED;
  }
  return DIAG_PASSED;
}
