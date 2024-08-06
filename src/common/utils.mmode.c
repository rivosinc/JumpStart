// SPDX-FileCopyrightText: 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "utils.mmode.h"
#include "cpu_bits.h"
#include "jumpstart.h"

__attribute__((section(".jumpstart.text.mmode"))) int32_t
mmode_try_get_seed(void) {
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
      jumpstart_mmode_fail();
    }
  }

  return (int32_t)get_field(seed, SEED_ENTROPY_MASK);
}

#define RAND_MAX 0x7fffffff
__attribute__((section(".jumpstart.data.mmode"))) uint64_t next = 1;
__attribute__((section(".jumpstart.text.mmode"))) uint64_t
__mmode_random(void) {
  /* Based on rand in diags/perf/membw/libc_replacement.h */
  /* This multiplier was obtained from Knuth, D.E., "The Art of
     Computer Programming," Vol 2, Seminumerical Algorithms, Third
     Edition, Addison-Wesley, 1998, p. 106 (line 26) & p. 108 */
  next = next * __extension__ 6364136223846793005LL + 1;
  return (int64_t)((next >> 32) & RAND_MAX);
}

__attribute__((section(".jumpstart.text.mmode"))) int32_t
get_random_number_from_mmode(void) {
  return (int32_t)__mmode_random();
}

__attribute__((section(".jumpstart.text.mmode"))) void
set_random_seed_from_mmode(int32_t seed) {
  next = (uint64_t)seed;
}
