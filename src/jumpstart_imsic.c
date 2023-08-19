// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include <stdint.h>

#include "jumpstart_defines.h"
#include "jumpstart_functions.h"
#include "jumpstart_imsic.h"

#define IMSIC_DISABLE_EIDELIVERY  0
#define IMSIC_ENABLE_EIDELIVERY   1

#define IMSIC_DISABLE_EITHRESHOLD 1
#define IMSIC_ENABLE_EITHRESHOLD  0

#define IMSIC_EIDELIVERY          0x70
#define IMSIC_EITHRESHOLD         0x72

#define IMSIC_EIP0                0x80
#define IMSIC_EIPx_BITS           32

#define IMSIC_EIE0                0xc0

#define imsic_s_csr_write(__c, __v)                                            \
  do {                                                                         \
    write_csr(siselect, __c);                                                  \
    write_csr(sireg, __v);                                                     \
  } while (0)

#define imsic_s_csr_set(__c, __v)                                              \
  do {                                                                         \
    write_csr(siselect, __c);                                                  \
    set_csr(sireg, __v);                                                       \
  } while (0)

#define imsic_s_csr_clear(__c, __v)                                            \
  do {                                                                         \
    write_csr(siselect, __c);                                                  \
    clear_csr(sireg, __v);                                                     \
  } while (0)

typedef enum EIX_REG_TYPE {
  EIX_REG_PENDING,
  EIX_REG_ENABLED,
} eix_reg_type_t;

typedef enum REG_BIT_ACTION {
  REG_BIT_SET,
  REG_BIT_CLEAR,
} reg_bit_action_t;

static void __imsic_eix_update(unsigned long id,
                               eix_reg_type_t reg_type,
                               reg_bit_action_t action)
    __attribute__((section(".jumpstart.text.supervisor")));

static void __imsic_eix_update(unsigned long id,
                               eix_reg_type_t reg_type,
                               reg_bit_action_t action) {
  unsigned long isel, ireg;

  isel = id / __riscv_xlen;
  isel *= __riscv_xlen / IMSIC_EIPx_BITS;
  isel += (reg_type == EIX_REG_PENDING) ? IMSIC_EIP0 : IMSIC_EIE0;

  ireg = 1ULL << (id & (__riscv_xlen - 1));

  if (action == REG_BIT_SET)
    imsic_s_csr_set(isel, ireg);
  else
    imsic_s_csr_clear(isel, ireg);
}

void imsic_id_enable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_SET);
}

void imsic_id_disable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_CLEAR);
}

void imsic_init(void) {
  imsic_s_csr_write(IMSIC_EITHRESHOLD, IMSIC_ENABLE_EITHRESHOLD);
  imsic_s_csr_write(IMSIC_EIDELIVERY, IMSIC_ENABLE_EIDELIVERY);
}

void imsic_fini(void) {
  imsic_s_csr_write(IMSIC_EIDELIVERY, IMSIC_DISABLE_EIDELIVERY);
  imsic_s_csr_write(IMSIC_EITHRESHOLD, IMSIC_DISABLE_EITHRESHOLD);
}

void send_ipi_to_supervisor_mode(unsigned long hart_id) {
  uintptr_t addr = IMSIC_S_BASE + IMSIC_S_INTERLEAVE * hart_id;

  *(uint32_t *)addr = IMSIC_IPI_ID;
}
