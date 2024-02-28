// SPDX-FileCopyrightText: 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <inttypes.h>

struct bit_range {
  uint8_t msb;
  uint8_t lsb;
};

uint64_t extract_bits(uint64_t value, struct bit_range range);
uint64_t place_bits(uint64_t value, uint64_t bits, struct bit_range range);
