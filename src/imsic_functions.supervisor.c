// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <stdint.h>

#include "imsic_functions.supervisor.h"
#include "jumpstart_defines.h"
#include "jumpstart_functions.h"

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

// Writes `__v` to the register `__c` of the guest IMSIC file selected by
// `vgein`.
#define imsic_vs_csr_write(__c, __v)                                           \
  do {                                                                         \
    write_csr(vsiselect, __c);                                                 \
    write_csr(vsireg, __v);                                                    \
  } while (0)

// Sets the bits specified by `__v` in the register `__c` of the guest IMSIC
// file selected by `vgein`.
#define imsic_vs_csr_set(__c, __v)                                             \
  do {                                                                         \
    write_csr(vsiselect, __c);                                                 \
    set_csr(vsireg, __v);                                                      \
  } while (0)

// Clears the bits specified by `__v` in the register `__c` of the guest IMSIC
// file selected by `vgein`.
#define imsic_vs_csr_clear(__c, __v)                                           \
  do {                                                                         \
    write_csr(vsiselect, __c);                                                 \
    clear_csr(vsireg, __v);                                                    \
  } while (0)

// Sets the vgein field of hstatus to the given guest_id. This selects the
// IMSIC file for that guest so that access to registers through viselect and
// vireg are directed to that interrupt file.
__attribute__((section(".jumpstart.text.supervisor"))) static void
set_vgein(unsigned guest_id) {
  uint64_t hstatus_val = read_csr(hstatus);
  hstatus_val &= ~((uint64_t)HSTATUS_VGEIN_MASK << HSTATUS_VGEIN_LSB);
  hstatus_val |=
      ((guest_id & (uint64_t)HSTATUS_VGEIN_MASK) << HSTATUS_VGEIN_LSB);
  write_csr(hstatus, hstatus_val);
}

// Sets or clears the bits specified in the given IMSIC register.
// Args:
// reg_idx - the IMSIC register to modify.
// mask - the bits to set or clear.
// set - if true set the bits given in mask, otherwise clear them.
// guest_id - the guest interrupt file to modify. If 0, modify the host.
__attribute__((section(".jumpstart.text.supervisor"))) static void
__imsic_eix_update_bits(unsigned long reg_idx, unsigned long mask,
                        reg_bit_action_t action, unsigned guest_id) {
  if (guest_id == 0) { // host(s-mode)
    if (action == REG_BIT_SET)
      imsic_s_csr_set(reg_idx, mask);
    else
      imsic_s_csr_clear(reg_idx, mask);
  } else {
    set_vgein(guest_id);
    if (action == REG_BIT_SET)
      imsic_vs_csr_set(reg_idx, mask);
    else
      imsic_vs_csr_clear(reg_idx, mask);
  }
}

__attribute__((section(".jumpstart.text.supervisor"))) static void
__imsic_eix_update(unsigned long interrupt_id, eix_reg_type_t reg_type,
                   reg_bit_action_t action, unsigned guest_id) {
  unsigned long isel, ireg;

  isel = interrupt_id / __riscv_xlen;
  isel *= __riscv_xlen / IMSIC_EIPx_BITS;
  isel += (reg_type == EIX_REG_PENDING) ? IMSIC_EIP0 : IMSIC_EIE0;

  ireg = 1ULL << (interrupt_id & (__riscv_xlen - 1));

  __imsic_eix_update_bits(isel, ireg, action, guest_id);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_id_enable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_SET, 0);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_id_disable(unsigned long id) {
  __imsic_eix_update(id, EIX_REG_ENABLED, REG_BIT_CLEAR, 0);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_id_enable_guest(unsigned guest_id, unsigned long interrupt_id) {
  __imsic_eix_update(interrupt_id, EIX_REG_ENABLED, REG_BIT_SET, guest_id);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_id_disable_guest(unsigned guest_id, unsigned long interrupt_id) {
  __imsic_eix_update(interrupt_id, EIX_REG_ENABLED, REG_BIT_CLEAR, guest_id);
}

__attribute__((section(".jumpstart.text.supervisor"))) void imsic_init(void) {
  imsic_s_csr_write(IMSIC_EITHRESHOLD, IMSIC_ENABLE_EITHRESHOLD);
  imsic_s_csr_write(IMSIC_EIDELIVERY, IMSIC_ENABLE_EIDELIVERY);
}

__attribute__((section(".jumpstart.text.supervisor"))) void imsic_fini(void) {
  imsic_s_csr_write(IMSIC_EIDELIVERY, IMSIC_DISABLE_EIDELIVERY);
  imsic_s_csr_write(IMSIC_EITHRESHOLD, IMSIC_DISABLE_EITHRESHOLD);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_enable_guest(unsigned guest_id) {
  set_vgein(guest_id);
  imsic_vs_csr_write(IMSIC_EITHRESHOLD, IMSIC_ENABLE_EITHRESHOLD);
  imsic_vs_csr_write(IMSIC_EIDELIVERY, IMSIC_ENABLE_EIDELIVERY);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
imsic_disable_guest(unsigned guest_id) {
  set_vgein(guest_id);
  imsic_vs_csr_write(IMSIC_EIDELIVERY, IMSIC_DISABLE_EIDELIVERY);
  imsic_vs_csr_write(IMSIC_EITHRESHOLD, IMSIC_DISABLE_EITHRESHOLD);
}

__attribute__((section(".jumpstart.text.supervisor"))) void
send_ipi_to_supervisor_mode(unsigned long hart_id) {
  uintptr_t addr = IMSIC_S_BASE + IMSIC_S_INTERLEAVE * hart_id;

  *(uint32_t *)addr = IMSIC_IPI_ID;
}

__attribute__((section(".jumpstart.text.supervisor"))) void
send_interrupt_to_guest(unsigned long hart_id, unsigned long guest_id,
                        uint32_t interrupt_id) {
  uintptr_t hart_base = IMSIC_S_BASE + IMSIC_S_INTERLEAVE * hart_id;
  uintptr_t addr =
      hart_base + IMSIC_GUEST_OFFSET + (guest_id - 1) * IMSIC_MMIO_PAGE_SIZE;

  *(uint32_t *)addr = interrupt_id;
}

__attribute__((section(".jumpstart.text.supervisor"))) uint64_t
imsic_next_pending_interrupt(unsigned guest_id) {
  set_vgein(guest_id);
  uint64_t vstopei = read_write_csr(vstopei, 0);
  return vstopei >> IMSIC_TOPEI_VAL_SHIFT;
}
