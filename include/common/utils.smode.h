// SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <inttypes.h>

struct bit_range {
  uint8_t msb;
  uint8_t lsb;
};

uint64_t extract_bits(uint64_t value, struct bit_range range);
uint64_t place_bits(uint64_t value, uint64_t bits, struct bit_range range);

int32_t smode_try_get_seed(void);
int32_t get_random_number_from_smode(void);
void set_random_seed_from_smode(int32_t seed);
