// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"
#include "utils.mmode.h"
#include "utils.smode.h"

#include <stdbool.h>
#include <string.h>

#define MISS_LIMIT 5

#define CHECK_SEED(flt_cnt, local_cnt, curr_seed, last_seed, misses)           \
  if (flt_cnt[hart_id] != local_cnt)                                           \
    jumpstart_mmode_fail();                                                    \
  if (curr_seed == last_seed) {                                                \
    misses++;                                                                  \
    if (misses > MISS_LIMIT)                                                   \
      jumpstart_mmode_fail();                                                  \
  }

#define SCHECK_SEED(flt_cnt, local_cnt, curr_seed, last_seed, misses)          \
  if (flt_cnt[hart_id] != local_cnt)                                           \
    jumpstart_smode_fail();                                                    \
  if (curr_seed == last_seed) {                                                \
    misses++;                                                                  \
    if (misses > MISS_LIMIT)                                                   \
      jumpstart_smode_fail();                                                  \
  }

__attribute__((section(".data.smode"))) volatile uint64_t
    fault_count_s[MAX_NUM_HARTS_SUPPORTED] = {0};

__attribute__((section(".text.smode"))) static void
smode_exception_handler(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_smode();
  unsigned long epc = get_sepc_for_current_exception();
  uint64_t tval = read_csr(stval);

  fault_count_s[hart_id]++;

  // skip over the faulting load
  if ((tval & 0x3) == 0x3)
    epc += 4;
  else
    epc += 2;

  set_sepc_for_current_exception(epc);
}

__attribute__((section(".text.smode"))) int smode_main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_smode();
  uint32_t seed = 0, last_seed = 0;
  int rand = 0, last_rand = 0;
  uint64_t temp = 65321512512;
  uint32_t faults = 0;
  uint32_t miss = 0;

  register_smode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST,
                                       (uint64_t)(smode_exception_handler));

  /* Test M-mode access. */
  int random = smode_try_get_seed();
  if (random < 0 || fault_count_s[hart_id] != 0)
    jumpstart_smode_fail();

  set_random_seed_from_smode((int)random);
  for (int i = 0; i < 1024; i++) {
    rand = get_random_number_from_smode();
    if (rand == last_rand)
      return DIAG_FAILED;

    last_rand = rand;
  }

  for (unsigned i = 0; i < 1024; i++) {
    /* Try csrrwi, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrwi %0, seed, 5" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrwi with zero imm, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrwi %0, seed, 0" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrs with x0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrs %0, seed, x0" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrc with x0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrc %0, seed, x0" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrs with rs1 != x0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrs %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrc with rs1 != x0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrc %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrsi with uimm=0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrsi %0, seed, 0" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrci with uimm=0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrci %0, seed, 0" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrsi with uimm != 0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrsi %0, seed, 1" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrci with uimm != 0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrc %0, seed, 31" : "=r"(seed)::"memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    SCHECK_SEED(fault_count_s, faults, seed, last_seed, miss);
  }

  return DIAG_PASSED;
}

volatile uint64_t fault_count[MAX_NUM_HARTS_SUPPORTED] = {0};

static void mmode_exception_handler(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_mmode();
  unsigned long epc = get_mepc_for_current_exception();
  uint64_t mtval = read_csr(mtval);

  fault_count[hart_id]++;

  // skip over the faulting load
  if ((mtval & 0x3) == 0x3)
    epc += 4;
  else
    epc += 2;

  set_mepc_for_current_exception(epc);
}

int main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_mmode();
  uint32_t seed = 0, last_seed = 0;
  int rand = 0, last_rand = 0;
  uint64_t temp = 65321512512;
  uint32_t faults = 0;
  uint32_t miss = 0;

  register_mmode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST,
                                       (uint64_t)(mmode_exception_handler));
  /* Test M-mode access. */
  int random = mmode_try_get_seed();
  if (random < 0 || fault_count[hart_id] != 0)
    jumpstart_mmode_fail();

  set_random_seed_from_mmode((int)random);
  for (int i = 0; i < 1024; i++) {
    rand = get_random_number_from_mmode();
    if (rand == last_rand)
      return DIAG_FAILED;

    last_rand = rand;
  }

  for (unsigned i = 0; i < 1024; i++) {
    /* Try csrrwi, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrwi %0, seed, 5" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrwi with zero imm, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrwi %0, seed, 0" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrs with x0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrs %0, seed, x0" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrc with x0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrc %0, seed, x0" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrs with rs1 != x0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrs %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrc with rs1 != x0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrc %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrsi with uimm=0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrsi %0, seed, 0" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrci with uimm=0, it should fault. */
    last_seed = seed;
    faults++;
    __asm__ __volatile__("csrrci %0, seed, 0" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrsi with uimm != 0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrsi %0, seed, 1" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrci with uimm != 0, shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrc %0, seed, 31" : "=r"(seed)::"memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);

    /* Try csrrw, it shouldn't fault. */
    last_seed = seed;
    __asm__ __volatile__("csrrw %0, seed, %1"
                         : "=r"(seed)
                         : "rK"(temp)
                         : "memory");
    CHECK_SEED(fault_count, faults, seed, last_seed, miss);
  }

  set_csr(mseccfg, MSECCFG_SSEED);
  if (run_function_in_smode((uint64_t)smode_main) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
