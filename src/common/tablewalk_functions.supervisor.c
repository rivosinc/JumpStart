// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "tablewalk_functions.supervisor.h"
#include "jumpstart_functions.h"

struct bit_range {
  uint8_t msb;
  uint8_t lsb;
};

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
    {.satp_mode = SATP_MODE_SV39,
     .pte_size_in_bytes = 8,
     .num_levels = 3,
     .va_vpn_bits = {{38, 30}, {29, 21}, {20, 12}},
     .pa_ppn_bits = {{55, 30}, {29, 21}, {20, 12}},
     .pte_ppn_bits = {{53, 28}, {27, 19}, {18, 10}}},

    {.satp_mode = SATP_MODE_SV48,
     .pte_size_in_bytes = 8,
     .num_levels = 4,
     .va_vpn_bits = {{47, 39}, {38, 30}, {29, 21}, {20, 12}},
     .pa_ppn_bits = {{55, 39}, {38, 30}, {29, 21}, {20, 12}},
     .pte_ppn_bits = {{53, 37}, {36, 28}, {27, 19}, {18, 10}}},
};

__attribute__((section(".jumpstart.text.supervisor"))) static uint64_t
extract_bits(uint64_t value, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return ((value >> lsb) & ((1ULL << (msb - lsb + 1)) - 1));
}

__attribute__((section(".jumpstart.text.supervisor"))) static uint64_t
place_bits(uint64_t value, uint64_t bits, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return (value & ~(((1ULL << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
translate_VA(uint64_t va, struct translation_info *xlate_info) {
  // C reimplementation of the DiagAttributes.translate_VA() from
  // generate_diag_sources.py.
  uint64_t satp_value = read_csr(satp);
  xlate_info->satp_mode = (uint8_t)(satp_value >> SATP_MODE_LSB);

  xlate_info->va = va;

  xlate_info->pa = 0;
  xlate_info->levels_traversed = 0;
  xlate_info->walk_successful = 0;
  for (uint8_t i = 0; i < MAX_NUM_PAGE_TABLE_LEVELS; ++i) {
    xlate_info->pte_address[i] = 0;
    xlate_info->pte_value[i] = 0;
  }

  if (xlate_info->satp_mode == SATP_MODE_BARE) {
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
    jumpstart_supervisor_fail();
  }

  // Step 1
  uint64_t a = (satp_value & SATP_PPN_MASK) << PAGE_OFFSET;

  uint8_t current_level = 0;

  // Step 2
  while (1) {
    xlate_info->pte_address[current_level] =
        a + extract_bits(va, mmu_mode_attribute->va_vpn_bits[current_level]) *
                mmu_mode_attribute->pte_size_in_bytes;

    uint64_t pte_value = *((uint64_t *)xlate_info->pte_address[current_level]);
    xlate_info->pte_value[current_level] = pte_value;

    ++(xlate_info->levels_traversed);

    if (extract_bits(pte_value, (struct bit_range){PTE_VALID_BIT_MSB,
                                                   PTE_VALID_BIT_LSB}) == 0) {
      // PTE is not valid. stop the walk.
      return;
    }

    uint8_t xwr = (uint8_t)extract_bits(
        pte_value, (struct bit_range){PTE_XWR_BIT_MSB, PTE_XWR_BIT_LSB});

    if ((xwr & 0x3) == 0x2) {
      // PTE at pte_address has R=0 and W=1.
      // TODO: Should we just return?
      jumpstart_supervisor_fail();
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
    } else if (extract_bits(pte_value,
                            (struct bit_range){PTE_A_BIT_MSB, PTE_A_BIT_LSB}) !=
               0) {
      // PTE has A=1 but is not a Leaf PTE.
      // TODO: Should we just return?
      jumpstart_supervisor_fail();
    } else if (extract_bits(pte_value,
                            (struct bit_range){PTE_D_BIT_MSB, PTE_D_BIT_LSB}) !=
               0) {
      // PTE has D=1 but is not a Leaf PTE
      // TODO: Should we just return?
      jumpstart_supervisor_fail();
    }

    ++current_level;
    if (current_level >= mmu_mode_attribute->num_levels) {
      // Ran out of levels
      jumpstart_supervisor_fail();
    }
  }

  xlate_info->pa = a + extract_bits(va, (struct bit_range){PAGE_OFFSET, 0});
  xlate_info->walk_successful = 1;
}
