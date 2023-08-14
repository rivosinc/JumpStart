# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.supervisor, "ax"

.global jump_to_main_in_supervisor_mode
jump_to_main_in_supervisor_mode:
  li  t0, SUPERVISOR_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  jal enable_mmu_from_supervisor_mode

  call main

  # TODO: Make sure we're in supervisor mode at this point.

  # a0 contains the exit code.
  li  a7, SYSCALL_JUMP_TO_MACHINE_MODE_AND_EXIT
  ecall

  call jumpstart_supervisor_fail

.global enable_mmu_from_supervisor_mode
enable_mmu_from_supervisor_mode:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_diag_satp_mode_from_supervisor_mode
  mv s2, a0

  slli  s2, s2, SATP_MODE_LSB

  jal get_diag_satp_ppn_from_supervisor_mode

  add  a0, a0, s2
  csrw  satp, a0
  sfence.vma

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global disable_mmu_from_supervisor_mode
disable_mmu_from_supervisor_mode:
  li  t0, 0
  csrw  satp, t0
  sfence.vma
  ret

# The stvec.base must always be 4 byte aligned.
.align 2
.global stvec_trap_handler
stvec_trap_handler:
  # Hold the a0 passed to us in a temporary till we're ready to save it away.
  csrw sscratch, a0

  csrr a0, sstatus
  andi a0, a0, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  beqz a0, 1f

  # We are in S-mode handling a trap from S-mode, use the
  # smode reg context save region.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  j save_context

1:
  # We are in S-mode handling a trap from U-mode, use the
  # umode reg context save region.

  # Save away the U-mode stack.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd sp, SP_OFFSET_IN_SAVE_REGION(gp)
  # and switch to the S-mode stack as we can't use the Umode stack.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(sp)
  ld sp, SP_OFFSET_IN_SAVE_REGION(sp)

save_context:
  # Restore the a0 passed to us when entering the trap handler.
  csrr a0, sscratch

  SAVE_ALL_GPRS


  # Change current mode to S.
  li  t0, SUPERVISOR_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  # Get the address of the trap handler if the test has registered one, else 0.
  csrr a0, scause
  call get_trap_handler_override

  beqz a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  jalr ra, a0

  # Restore the context from before the trap.
  csrr a0, sstatus
  andi a0, a0, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  beqz a0, switch_to_umode_stack
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  j restore_context

switch_to_umode_stack:
  li  t0, USER_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

restore_context:
  RESTORE_ALL_GPRS

  sret

check_for_env_call_requests:
  csrr a0, scause
  li t0, SCAUSE_EC_ENV_CALL_FROM_UMODE
  beq a0, t0, handle_env_call_from_umode

  j jumpstart_supervisor_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RETURN_TO_SUPERVISOR_MODE
  beq a7, t0, env_call_return_to_supervisor_mode

  j jumpstart_supervisor_fail

.global jumpstart_supervisor_fail
jumpstart_supervisor_fail:
  # TODO: This is a temporary fail handler. We need to figure out
  wfi

env_call_return_to_supervisor_mode:
  # This is the return to supervisor path for run_function_in_user_mode().

  # Restore S mode context and return status in a0
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a1, SEPC_OFFSET_IN_SAVE_REGION(gp)
  csrw sepc, a1

  ld a1, SSTATUS_OFFSET_IN_SAVE_REGION(gp)
  li a2, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  or a1, a1, a2
  csrw sstatus, a1

  RESTORE_ALL_GPRS

  sret

# A0 contains the address of the function to run in usermode.
.global run_function_in_user_mode
run_function_in_user_mode:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  # Pass a0 to usermode as argument.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd a0, A0_OFFSET_IN_SAVE_REGION(gp)

  GET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  li  t1, SUPERVISOR_MODE_ENCODING
  bne t0, t1, jumpstart_supervisor_fail

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, sstatus
  sd t0, SSTATUS_OFFSET_IN_SAVE_REGION(gp)

  la  t0, smode_return
  sd t0, SEPC_OFFSET_IN_SAVE_REGION(gp)

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la a1, jump_to_function_in_umode
  csrw sepc, a1

  li t0, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  csrc sstatus, t0

  # Switch to the U-mode stack.
  GET_THREAD_ATTRIBUTES_HART_ID(t0)
  li  t1, (NUM_PAGES_PER_HART_FOR_UMODE_STACK * 4096)
  mul t0, t0, t1
  la  t2, umode_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  li  t0, USER_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  sret

smode_return:
  # Usermode return status using a0. Given umode returns through ecall, we save
  # a0 to umode_reg_context_save_region in ecall handler and return to this point to continue
  # s-mode execution from the place we left it.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# User mode code. Don't add any supervisor mode code in this section.
.section .jumpstart.text.umode, "ax"

# A0 contains the address of the function to jump to.
.global jump_to_function_in_umode
jump_to_function_in_umode:

  # A0 contains arg value passed by S mode.
  jalr ra, a0

  # a0 contains the exit code.
  li  a7, SYSCALL_RETURN_TO_SUPERVISOR_MODE
  ecall

  # We shouldn't come back here.
  wfi


.section .jumpstart.data.privileged, "aw"

.global hart_status_tracker
hart_status_tracker:
  .rept MAX_NUM_HARTS_SUPPORTED
      .byte HART_INACTIVE
  .endr
