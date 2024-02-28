// SPDX-FileCopyrightText: 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "utils.smode.h"

__attribute__((section(".jumpstart.text.smode"))) __attribute__((const))
uint64_t
extract_bits(uint64_t value, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return ((value >> lsb) & ((1ULL << (msb - lsb + 1)) - 1));
}

__attribute__((section(".jumpstart.text.smode"))) __attribute__((const))
uint64_t
place_bits(uint64_t value, uint64_t bits, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return (value & ~(((1ULL << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb);
}
