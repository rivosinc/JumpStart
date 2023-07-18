# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

#define T0_OFFSET  (0 * 8)
#define T1_OFFSET  (1 * 8)
#define T2_OFFSET  (2 * 8)
#define T3_OFFSET  (3 * 8)
#define T4_OFFSET  (4 * 8)
#define T5_OFFSET  (5 * 8)
#define T6_OFFSET  (6 * 8)
#define A0_OFFSET  (7 * 8)
#define A1_OFFSET  (8 * 8)
#define A2_OFFSET  (9 * 8)
#define A3_OFFSET  (10 * 8)
#define A4_OFFSET  (11 * 8)
#define A5_OFFSET  (12 * 8)
#define A6_OFFSET  (13 * 8)
#define A7_OFFSET  (14 * 8)
#define RA_OFFSET  (15 * 8)

.section .jumpstart.data, "aw"

.global exception_reg_region
exception_reg_region:
.rep 16
  .8byte 0x0000000000000000
.endr

.section .jumpstart.text, "ax"

.global supervisor_jump_to_main
supervisor_jump_to_main:
  la t0, stvec_trap_handler
  csrw stvec, t0

  li  a0, SUPERVISOR_MODE_ENCODING
  call set_thread_attributes_current_mode

  li a0, (1 << SIE_EXT_INTERRUPT)
  csrw sie, a0

  li a0, (1 << SSTATUS_SIE_SHIFT)
  csrs sstatus, a0

  call main

  # TODO: Make sure we're in supervisor mode at this point.

  # a0 contains the exit code.
  li  a7, SYSCALL_JUMP_TO_MACHINE_MODE_AND_EXIT
  ecall

  call jumpstart_supervisor_fail

.global setup_mmu_for_supervisor_mode
setup_mmu_for_supervisor_mode:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_diag_satp_mode
  mv s2, a0

  slli  s2, s2, SATP_MODE_LSB

  jal get_diag_satp_ppn

  add  a0, a0, s2
  csrw  satp, a0
  sfence.vma

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global disable_mmu_for_supervisor_mode
disable_mmu_for_supervisor_mode:
  li  t0, 0
  csrw  satp, t0
  sfence.vma
  ret

# The stvec.base must always be 4 byte aligned.
.align 2
.global stvec_trap_handler
stvec_trap_handler:
  csrw sscratch, a0
  la a0, exception_reg_region

  sd t0, T0_OFFSET(a0)
  sd t1, T1_OFFSET(a0)
  sd t2, T2_OFFSET(a0)
  sd t3, T3_OFFSET(a0)
  sd t4, T4_OFFSET(a0)
  sd t5, T5_OFFSET(a0)
  sd t6, T6_OFFSET(a0)
  sd a1, A1_OFFSET(a0)
  sd a2, A2_OFFSET(a0)
  sd a3, A3_OFFSET(a0)
  sd a4, A4_OFFSET(a0)
  sd a5, A5_OFFSET(a0)
  sd a6, A6_OFFSET(a0)
  sd a7, A7_OFFSET(a0)
  sd ra, RA_OFFSET(a0)

  mv t0, a0
  csrr a0, sscratch
  sd a0, A0_OFFSET(t0)

  li  a0, SUPERVISOR_MODE_ENCODING
  jal set_thread_attributes_current_mode

  csrr a0, scause
  # returns the address of the trap handler if the user
  # has registered one, else 0.
  call get_trap_handler_override

  beqz a0, 1f

  jalr ra, a0
  j jumpstart_supervisor_return

1:
  csrr a0, scause
  li t0, SCAUSE_EC_ENV_CALL_FROM_UMODE
  beq a0, t0, handle_env_call_from_umode

  j jumpstart_supervisor_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  j jumpstart_supervisor_fail

.global jumpstart_supervisor_fail
jumpstart_supervisor_fail:
  # TODO: This is a temporary fail handler. We need to figure out
  wfi

.global jumpstart_supervisor_return
jumpstart_supervisor_return:
  la a0, exception_reg_region

  ld t0, T0_OFFSET(a0)
  ld t1, T1_OFFSET(a0)
  ld t2, T2_OFFSET(a0)
  ld t3, T3_OFFSET(a0)
  ld t4, T4_OFFSET(a0)
  ld t5, T5_OFFSET(a0)
  ld t6, T6_OFFSET(a0)
  ld a1, A1_OFFSET(a0)
  ld a2, A2_OFFSET(a0)
  ld a3, A3_OFFSET(a0)
  ld a4, A4_OFFSET(a0)
  ld a5, A5_OFFSET(a0)
  ld a6, A6_OFFSET(a0)
  ld a7, A7_OFFSET(a0)
  ld ra, RA_OFFSET(a0)
  ld a0, A0_OFFSET(a0)

  sret
