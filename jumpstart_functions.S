# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .text

.global setup_thread_attributes
setup_thread_attributes:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  csrr  t0, mhartid
  li  t2, THREAD_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t2, t0, t2
  la  t1, thread_attributes_region
  add tp, t1, t2

  csrr  a0, mhartid
  jal set_thread_hart_id

  li  a0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE
  jal set_thread_bookend_magic_number

  li  a0, MSTATUS_MPP_MACHINE_MODE
  jal set_thread_current_mode

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.global disable_mmu_for_supervisor_mode
disable_mmu_for_supervisor_mode:
  li  t0, 0
  csrw  satp, t0
  fence.i
  ret

.global setup_mmu_for_supervisor_mode
setup_mmu_for_supervisor_mode:
    addi  sp, sp, -16
    sd  ra, 8(sp)
    sd  fp, 0(sp)
    addi    fp, sp, 16

    jal get_diag_satp_mode
    mv s2, a0

    jal get_diag_satp_mode_lsb
    sll  s2, s2, a0

    jal get_diag_satp_ppn

    add  a0, a0, a2
    csrw  satp, a0
    fence.i

    ld  ra, 8(sp)
    ld  fp, 0(sp)
    addi  sp, sp, 16
    ret

#define MSTATUS_SUPERVISOR_SWITCH 0x0000000a00000800

.global jump_to_supervisor_mode
jump_to_supervisor_mode:

  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_current_mode
  li  t1, MSTATUS_MPP_MACHINE_MODE
  bne a0, t1, jumpstart_fail

  la  t0, 1f
  csrw  mepc, t0
  csrr  t0, mstatus
  li  t1, MSTATUS_SUPERVISOR_SWITCH
  or  t0, t0, t1
  csrw  mstatus, t0
  mret

1:
  li  a0, MSTATUS_MPP_SUPERVISOR_MODE
  jal set_thread_current_mode

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret
