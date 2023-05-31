# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .text.jumpstart

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

  li t0, TRAP_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t0, a0, t0
  la t1, trap_handler_overrides
  add a0, t1, t0
  la t1, trap_handler_overrides_end
  # Make sure that we've allocated enough space for this core's trap handler
  # overrides.
  bgeu a0, t1, jumpstart_fail
  jal set_thread_trap_override_struct_address

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

    # Enable menvcfg.pbmte
    # The PBMTE bit controls whether the Svpbmt extension is
    # available for use in S-mode and G-stage address translation
    # (i.e., for page tables pointed to by satp or hgatp).
    #define MENVCFG_PBMTE_ENABLE (1 << 62)
    csrr  t0, menvcfg
    li  t1, MENVCFG_PBMTE_ENABLE
    or  t0, t0, t1
    csrw  menvcfg, t0

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

  # Already in supervisor mode
  li  t1, MSTATUS_MPP_SUPERVISOR_MODE
  beq a0, t1, 2f

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

2:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.global jump_to_machine_mode
jump_to_machine_mode:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_current_mode

  # Already in machine mode
  li  t1, MSTATUS_MPP_MACHINE_MODE
  beq a0, t1, 1f

  li  t1, MSTATUS_MPP_SUPERVISOR_MODE
  bne a0, t1, jumpstart_fail

  li  a7, SYSCALL_JUMP_TO_MACHINE_MODE
  ecall

1:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# syscall handlers

handle_env_call_from_smode:
  # a7 will contain the syscall number

  li t0, SYSCALL_JUMP_TO_MACHINE_MODE
  beq a7, t0, env_call_jump_to_machine_mode

  j jumpstart_fail

handle_env_call_from_mmode:
  # a7 will contain the syscall number

  j jumpstart_fail

env_call_jump_to_machine_mode:
  li  a0, MSTATUS_MPP_MACHINE_MODE
  jal set_thread_current_mode

  # MEPC will be pointing to the ECALL and we need to return to the
  # instruction following it.
  csrr ra, mepc
  addi ra, ra, 4
  ret

# END syscall handlers

# The mtvec.base must always be 4 byte aligned.
.align 2
.global mtvec_trap_handler
mtvec_trap_handler:
  li  a0, MSTATUS_MPP_MACHINE_MODE
  jal set_thread_current_mode

  csrr a0, mcause
  # returns the address of the trap handler if the user
  # has registered one, else 0.
  jal get_trap_handler_override

  beqz a0, 1f

  jalr x0, a0

1:
  csrr a0, mcause
  li t0, MCAUSE_EC_ENV_CALL_FROM_SMODE
  beq a0, t0, handle_env_call_from_smode

  j jumpstart_fail

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
