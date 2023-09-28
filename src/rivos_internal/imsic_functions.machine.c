// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <stdint.h>

#include "imsic_functions.h"
#include "imsic_functions.machine.h"
#include "jumpstart_defines.h"
#include "jumpstart_functions.h"

#define imsic_m_csr_write(__c, __v)                                            \
  do {                                                                         \
    write_csr(miselect, __c);                                                  \
    write_csr(mireg, __v);                                                     \
  } while (0)

#define imsic_m_csr_read(__c)                                                  \
  ({                                                                           \
    write_csr(miselect, __c);                                                  \
    read_csr(mireg);                                                           \
  })

#define imsic_m_csr_set(__c, __v)                                              \
  do {                                                                         \
    write_csr(miselect, __c);                                                  \
    set_csr(mireg, __v);                                                       \
  } while (0)

#define imsic_m_csr_clear(__c, __v)                                            \
  do {                                                                         \
    write_csr(miselect, __c);                                                  \
    clear_csr(mireg, __v);                                                     \
  } while (0)

// Sets or clears the bits specified in the given IMSIC register.
// Args:
// reg_idx - the IMSIC register to modify.
// mask - the bits to set or clear.
// set - if true set the bits given in mask, otherwise clear them.
__attribute__((section(".jumpstart.text.machine"))) static void
__imsic_eix_update_bits(unsigned long reg_idx, unsigned long mask,
                        reg_bit_action_t action) {
  if (action == REG_BIT_SET)
    imsic_m_csr_set(reg_idx, mask);
  else
    imsic_m_csr_clear(reg_idx, mask);
}

__attribute__((section(".jumpstart.text.machine"))) static void
__imsic_eix_update(unsigned long interrupt_id, eix_reg_type_t reg_type,
                   reg_bit_action_t action) {
  unsigned long isel, ireg;

  isel = interrupt_id / __riscv_xlen;
  isel *= __riscv_xlen / IMSIC_EIPx_BITS;
  isel += (reg_type == EIX_REG_PENDING) ? IMSIC_EIP0 : IMSIC_EIE0;

  ireg = 1ULL << (interrupt_id & (__riscv_xlen - 1));

  __imsic_eix_update_bits(isel, ireg, action);
}

__attribute__((section(".jumpstart.text.machine"))) static unsigned long
__imsic_eix_read(unsigned long interrupt_id, eix_reg_type_t reg_type) {
  unsigned long isel, mask;

  isel = interrupt_id / __riscv_xlen;
  isel *= __riscv_xlen / IMSIC_EIPx_BITS;
  isel += (reg_type == EIX_REG_PENDING) ? IMSIC_EIP0 : IMSIC_EIE0;

  mask = 1ULL << (interrupt_id & (__riscv_xlen - 1));

  return imsic_m_csr_read(isel) & mask;
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_id_enable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_SET);
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_id_disable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_CLEAR);
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_init(void) {
  imsic_m_csr_write(IMSIC_EITHRESHOLD, IMSIC_ENABLE_EITHRESHOLD);
  imsic_m_csr_write(IMSIC_EIDELIVERY, IMSIC_ENABLE_EIDELIVERY);
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_fini(void) {
  imsic_m_csr_write(IMSIC_EIDELIVERY, IMSIC_DISABLE_EIDELIVERY);
  imsic_m_csr_write(IMSIC_EITHRESHOLD, IMSIC_DISABLE_EITHRESHOLD);
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_update_eithreshold(uint32_t val) {
  imsic_m_csr_write(IMSIC_EITHRESHOLD, val);
}

__attribute__((section(".jumpstart.text.machine"))) void
imsic_machine_update_eidelivery(uint32_t val) {
  imsic_m_csr_write(IMSIC_EIDELIVERY, val);
}

__attribute__((section(".jumpstart.text.machine"))) unsigned long
imsic_machine_read_eip(unsigned long irq_id) {
  return __imsic_eix_read(irq_id, EIX_REG_PENDING);
}

__attribute__((section(".jumpstart.text.machine"))) void
send_interrupt_to_machine_mode(unsigned long hart_id, uint32_t irq) {
  uintptr_t addr = IMSIC_M_BASE + IMSIC_M_INTERLEAVE * hart_id;

  *(uint32_t *)addr = irq;
}

__attribute__((section(".jumpstart.text.machine"))) uint64_t
imsic_next_machine_pending_interrupt(void) {
  uint64_t mtopei = read_write_csr(mtopei, 0);
  return mtopei >> IMSIC_TOPEI_VAL_SHIFT;
}
