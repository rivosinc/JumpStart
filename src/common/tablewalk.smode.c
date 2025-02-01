/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "tablewalk.smode.h"
#include "cpu_bits.h"
#include "jumpstart.h"
#include "utils.smode.h"

struct mmu_mode_attribute {
  uint8_t satp_mode;
  uint8_t pte_size_in_bytes;
  uint8_t num_levels;
  struct bit_range va_vpn_bits[MAX_NUM_PAGE_TABLE_LEVELS];
  struct bit_range pa_ppn_bits[MAX_NUM_PAGE_TABLE_LEVELS];
  struct bit_range pte_ppn_bits[MAX_NUM_PAGE_TABLE_LEVELS];
};

// TODO: generate this from the Python.
const struct mmu_mode_attribute mmu_mode_attributes[] = {
    {.satp_mode = VM_1_10_SV39,
     .pte_size_in_bytes = 8,
     .num_levels = 3,
     .va_vpn_bits = {{38, 30}, {29, 21}, {20, 12}},
     .pa_ppn_bits = {{55, 30}, {29, 21}, {20, 12}},
     .pte_ppn_bits = {{53, 28}, {27, 19}, {18, 10}}},

    {.satp_mode = VM_1_10_SV48,
     .pte_size_in_bytes = 8,
     .num_levels = 4,
     .va_vpn_bits = {{47, 39}, {38, 30}, {29, 21}, {20, 12}},
     .pa_ppn_bits = {{55, 39}, {38, 30}, {29, 21}, {20, 12}},
     .pte_ppn_bits = {{53, 37}, {36, 28}, {27, 19}, {18, 10}}},
};

__attr_stext void translate_VA(uint64_t va,
                               struct translation_info *xlate_info) {
  // C reimplementation of the DiagSource.translate_VA() from
  // generate_diag_sources.py.
  uint64_t satp_value = read_csr(satp);
  xlate_info->satp_mode = (uint8_t)get_field(satp_value, SATP64_MODE);

  xlate_info->va = va;

  xlate_info->pa = 0;
  xlate_info->levels_traversed = 0;
  xlate_info->walk_successful = 0;
  for (uint8_t i = 0; i < MAX_NUM_PAGE_TABLE_LEVELS; ++i) {
    xlate_info->pte_address[i] = 0;
    xlate_info->pte_value[i] = 0;
  }

  if (xlate_info->satp_mode == VM_1_10_MBARE) {
    xlate_info->pa = va;
    xlate_info->walk_successful = 1;
    return;
  }

  const struct mmu_mode_attribute *mmu_mode_attribute = 0;
  for (uint8_t i = 0;
       i < sizeof(mmu_mode_attributes) / sizeof(struct mmu_mode_attribute);
       ++i) {
    if (mmu_mode_attributes[i].satp_mode == xlate_info->satp_mode) {
      mmu_mode_attribute = &mmu_mode_attributes[i];
      break;
    }
  }

  if (mmu_mode_attribute == 0) {
    jumpstart_smode_fail();
  }

  // Step 1
  uint64_t a = (satp_value & SATP64_PPN) << PAGE_OFFSET;

  uint8_t current_level = 0;

  // Step 2
  while (1) {
    xlate_info->pte_address[current_level] =
        a + extract_bits(va, mmu_mode_attribute->va_vpn_bits[current_level]) *
                mmu_mode_attribute->pte_size_in_bytes;

    uint64_t pte_value = *((uint64_t *)xlate_info->pte_address[current_level]);
    xlate_info->pte_value[current_level] = pte_value;

    ++(xlate_info->levels_traversed);

    if (get_field(pte_value, PTE_V) == 0) {
      // PTE is not valid. stop the walk.
      return;
    }

    uint8_t xwr = (uint8_t)get_field(pte_value, PTE_R | PTE_W | PTE_X);

    if ((xwr & 0x3) == 0x2) {
      // PTE at pte_address has R=0 and W=1.
      jumpstart_smode_fail();
    }

    a = 0;

    for (uint8_t ppn_id = 0; ppn_id < mmu_mode_attribute->num_levels;
         ++ppn_id) {
      uint64_t ppn_value =
          extract_bits(pte_value, mmu_mode_attribute->pte_ppn_bits[ppn_id]);
      a = place_bits(a, ppn_value, mmu_mode_attribute->pa_ppn_bits[ppn_id]);
    }

    if ((xwr & 0x6) || (xwr & 0x1)) {
      // This is a Leaf PTE. Done with the walk.
      break;
    } else if (get_field(pte_value, PTE_A) != 0) {
      // PTE has A=1 but is not a Leaf PTE.
      jumpstart_smode_fail();
    } else if (get_field(pte_value, PTE_D) != 0) {
      // PTE has D=1 but is not a Leaf PTE
      jumpstart_smode_fail();
    }

    ++current_level;
    if (current_level >= mmu_mode_attribute->num_levels) {
      // Ran out of levels
      jumpstart_smode_fail();
    }
  }

  xlate_info->pa = a + extract_bits(va, (struct bit_range){PAGE_OFFSET - 1, 0});
  xlate_info->walk_successful = 1;
}
