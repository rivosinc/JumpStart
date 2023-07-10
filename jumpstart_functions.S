# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text, "ax"

.global supervisor_entry_point
supervisor_entry_point:
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

  jal get_diag_satp_mode_lsb
  sll  s2, s2, a0

  jal get_diag_satp_ppn

  add  a0, a0, a2
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

.global jump_to_user_mode
jump_to_user_mode:

  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_attributes_current_mode

  # Already in user mode
  li  t1, USER_MODE_ENCODING
  beq a0, t1, 2f

  li  t1, SUPERVISOR_MODE_ENCODING
  bne a0, t1, jumpstart_supervisor_fail

  la  t0, 1f
  csrw  sepc, t0
  csrr  t0, sstatus
  li  t1, (USER_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  or  t0, t0, t1
  csrw  sstatus, t0
  sret

1:
  li  a0, USER_MODE_ENCODING
  jal set_thread_attributes_current_mode

2:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.global jump_to_supervisor_mode
jump_to_supervisor_mode:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_attributes_current_mode

  # Already in machine mode
  li  t1, SUPERVISOR_MODE_ENCODING
  beq a0, t1, 1f

  li  t1, USER_MODE_ENCODING
  bne a0, t1, jumpstart_supervisor_fail

  li  a7, SYSCALL_JUMP_TO_SUPERVISOR_MODE
  ecall

1:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# The stvec.base must always be 4 byte aligned.
.align 2
.global stvec_trap_handler
stvec_trap_handler:
  li  a0, SUPERVISOR_MODE_ENCODING
  jal set_thread_attributes_current_mode

  csrr a0, scause
  # returns the address of the trap handler if the user
  # has registered one, else 0.
  call get_trap_handler_override

  beqz a0, 1f

  jalr x0, a0

1:
  csrr a0, scause
  li t0, SCAUSE_EC_ENV_CALL_FROM_UMODE
  beq a0, t0, handle_env_call_from_umode

  j jumpstart_supervisor_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_JUMP_TO_SUPERVISOR_MODE
  beq a7, t0, env_call_jump_to_supervisor_mode

  j jumpstart_supervisor_fail

env_call_jump_to_supervisor_mode:
  # SEPC will be pointing to the ECALL and we need to return to the
  # instruction following it.
  csrr ra, sepc
  addi ra, ra, 4
  ret

.global jumpstart_supervisor_fail
jumpstart_supervisor_fail:
  # TODO: This is a temporary fail handler. We need to figure out
  wfi
