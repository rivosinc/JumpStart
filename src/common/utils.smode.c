/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "utils.smode.h"
#include "cpu_bits.h"
#include "jumpstart.h"

__attr_stext __attribute__((const)) uint64_t
extract_bits(uint64_t value, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return ((value >> lsb) & ((1ULL << (msb - lsb + 1)) - 1));
}

__attr_stext __attribute__((const)) uint64_t
place_bits(uint64_t value, uint64_t bits, struct bit_range range) {
  uint8_t msb = range.msb;
  uint8_t lsb = range.lsb;
  return (value & ~(((1ULL << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb);
}

__attr_stext int32_t smode_try_get_seed(void) {
  uint32_t seed;
  uint32_t i = 100;

  for (i = 100; i > 0; i--) {
    __asm__ __volatile__("csrrw %0, seed, x0" : "=r"(seed)::"memory");
    uint32_t opst = get_field(seed, SEED_OPST);
    if (opst == SEED_OPST_ES16) {
      break;
    } else if (opst == SEED_OPST_WAIT || opst == SEED_OPST_BIST) {
      continue;
    } else {
      jumpstart_smode_fail();
    }
  }

  return (int32_t)get_field(seed, SEED_ENTROPY_MASK);
}

#define RAND_MAX 0x7fffffff
__attr_sdata uint64_t snext = 1;

__attr_stext uint64_t __smode_random(void) {
  /* Based on rand in diags/perf/membw/libc_replacement.h */
  /* This multiplier was obtained from Knuth, D.E., "The Art of
     Computer Programming," Vol 2, Seminumerical Algorithms, Third
     Edition, Addison-Wesley, 1998, p. 106 (line 26) & p. 108 */
  snext = snext * __extension__ 6364136223846793005LL + 1;
  return (int64_t)((snext >> 32) & RAND_MAX);
}

__attr_stext int32_t get_random_number_from_smode(void) {
  return (int32_t)__smode_random();
}

__attr_stext void set_random_seed_from_smode(int32_t seed) {
  snext = (uint64_t)seed;
}
