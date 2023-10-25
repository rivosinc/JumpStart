# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.supervisor, "ax"

# a0 contains the address of the function to jump to.
.global jump_to_function_in_smode
jump_to_function_in_smode:
  li  t0, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  # A0 contains arg value passed by S mode.
  jalr ra, a0

  # a0 contains the exit code.
  li  a7, SYSCALL_RUN_FUNC_IN_SUPERVISOR_MODE_COMPLETE
  ecall

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
  li  gp, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)

  csrr  gp, sstatus
  andi  gp, gp, SSTATUS_SPP
  srli  gp, gp, SSTATUS_SPP_SHIFT
  addi  gp, gp, -PRV_S
  beqz  gp, handle_trap_from_supervisor_mode
  j  handle_trap_from_user_mode

handle_trap_from_supervisor_mode:
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, hstatus
  sd t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)

  j check_for_trap_handler_overrides

handle_trap_from_user_mode:
  # Save away the U-mode stack.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd sp, SP_OFFSET_IN_SAVE_REGION(gp)
  # and switch to the S-mode stack as we can't use the Umode stack.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(sp)
  ld sp, SP_OFFSET_IN_SAVE_REGION(sp)

  # We will save away the user mode context to the user mode region
  # which GP currently points to.
  SAVE_ALL_GPRS

check_for_trap_handler_overrides:
  # Check if the test has registered a trap handler for this trap.
  csrr a0, scause
  call get_supervisor_mode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

  csrr  gp, sstatus
  andi  gp, gp, SSTATUS_SPP
  srli  gp, gp, SSTATUS_SPP_SHIFT
  addi  gp, gp, -PRV_S
  bnez  gp, restore_user_mode_context

restore_supervisor_mode_context:
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  ld t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw hstatus, t0

  j restore_context

restore_user_mode_context:
  li  gp, PRV_U
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

restore_context:
  RESTORE_ALL_GPRS

# The return_from_stvec_trap_handler label is referenced in control transfer
# records diag so mark it as global.
.global return_from_stvec_trap_handler
return_from_stvec_trap_handler:
  sret

check_for_env_call_requests:
  csrr t0, scause
  li t1, RISCV_EXCP_U_ECALL
  beq t0, t1, handle_env_call_from_umode

  j jumpstart_supervisor_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_user_mode_complete

  j jumpstart_supervisor_fail

.global jumpstart_supervisor_fail
jumpstart_supervisor_fail:
  li a0, DIAG_FAILED
  li  a7, SYSCALL_RUN_FUNC_IN_SUPERVISOR_MODE_COMPLETE
  ecall

handle_syscall_run_func_in_user_mode_complete:
  # This is the return to supervisor path for run_function_in_user_mode().

  # Restore S mode context and return status in a0
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  ld a1, SSTATUS_OFFSET_IN_SAVE_REGION(gp)
  li a2, (PRV_S << SSTATUS_SPP_SHIFT)
  or a1, a1, a2
  csrw sstatus, a1

  RESTORE_ALL_GPRS

  la  ra, run_function_in_user_mode_return_point
  ret

# A0 contains the address of the function to run in usermode.
.global run_function_in_user_mode
run_function_in_user_mode:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  GET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)
  li  t1, PRV_S
  bne t0, t1, jumpstart_supervisor_fail

  # Pass a0 to usermode as argument.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd a0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, sstatus
  sd t0, SSTATUS_OFFSET_IN_SAVE_REGION(gp)

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la a1, jump_to_function_in_umode
  csrw sepc, a1

  li t0, (PRV_S << SSTATUS_SPP_SHIFT)
  csrc sstatus, t0

  # Switch to the U-mode stack.
  GET_THREAD_ATTRIBUTES_HART_ID(t0)
  li  t1, (NUM_PAGES_PER_HART_FOR_UMODE_STACK * 4096)
  mul t0, t0, t1
  la  t2, umode_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  li  t0, PRV_U
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  sret

run_function_in_user_mode_return_point:
  # Usermode return status using a0. Given umode returns through ecall, we save
  # a0 to umode_reg_context_save_region in ecall handler and return to this point to continue
  # s-mode execution from the place we left it.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret
