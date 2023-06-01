# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

# This section is placed immediately after the machine mode section
# start it on a new page. We'll use the supervisor_entry_point label to
# determine the end of the machine mode code area so that we can set
# up MCRR_0 correctly.
.section .text.jumpstart.supervisor.init

.align 12
.global supervisor_entry_point
supervisor_entry_point:
	la t0, stvec_trap_handler
	csrw stvec, t0

  li  a0, MSTATUS_MPP_SUPERVISOR_MODE
  jal set_thread_current_mode

  jal main

  # a0 contains the exit code.
  li  a7, SYSCALL_JUMP_TO_MACHINE_MODE_AND_EXIT
  ecall

  wfi

.section .text.jumpstart

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

.global disable_mmu_for_supervisor_mode
disable_mmu_for_supervisor_mode:
  li  t0, 0
  csrw  satp, t0
  fence.i
  ret

# The stvec.base must always be 4 byte aligned.
.align 2
.global stvec_trap_handler
stvec_trap_handler:
  li  a0, MSTATUS_MPP_SUPERVISOR_MODE
  jal set_thread_current_mode

  csrr a0, scause
  # returns the address of the trap handler if the user
  # has registered one, else 0.
  jal get_trap_handler_override

  beqz a0, 1f

  jalr x0, a0

1:
  j jumpstart_fail
