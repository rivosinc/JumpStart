# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.smode, "ax"

# a0 contains the address of the function to jump to.
# a1-a7 contains the arguments to pass to the smode function.
.global jump_to_function_in_smode
jump_to_function_in_smode:
  li  t0, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  mv t0, a0

  # Function arguments have to be passed in a0-a6.
  mv a0, a1
  mv a1, a2
  mv a2, a3
  mv a3, a4
  mv a4, a5
  mv a5, a6
  mv a6, a7

  jalr ra, t0

  # a0 contains the exit code.
  li  a7, SYSCALL_RUN_FUNC_IN_SMODE_COMPLETE
  ecall

.global disable_mmu_from_smode
disable_mmu_from_smode:
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
  beqz  gp, handle_trap_from_smode
  j  handle_trap_from_umode

handle_trap_from_smode:
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, hstatus
  sd t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)

  j check_for_trap_handler_overrides

handle_trap_from_umode:
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
  call get_smode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

  csrr  gp, sstatus
  andi  gp, gp, SSTATUS_SPP
  srli  gp, gp, SSTATUS_SPP_SHIFT
  addi  gp, gp, -PRV_S
  bnez  gp, restore_umode_context

restore_smode_context:
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  ld t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw hstatus, t0

  j restore_context

restore_umode_context:
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

  j jumpstart_smode_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_UMODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_umode_complete

  j jumpstart_smode_fail

.global jumpstart_smode_fail
jumpstart_smode_fail:
  li a0, DIAG_FAILED
  li  a7, SYSCALL_RUN_FUNC_IN_SMODE_COMPLETE
  ecall

handle_syscall_run_func_in_umode_complete:
  # This is the return to supervisor path for run_function_in_umode().

  # Re-enable interrupts that were disabled in run_function_in_umode().
  # Set SPIE to 1, on sret this will set SIE to 1.
  li  t0, (PRV_S << SSTATUS_SPP_SHIFT) | SSTATUS_SPIE
  csrs  sstatus, t0

  la  t0, run_function_in_umode_return_point
  csrw sepc, t0

  # Restore S mode context.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  RESTORE_ALL_GPRS

  # Return U-mode status using a0. a0 was saved to umode_reg_context_save_region
  # in stvec_trap_handler.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  sret

# Inputs:
#   a0: address of the function to run in usermode.
#   a1: arg0 to function to run in usermode.
.global run_function_in_umode
run_function_in_umode:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  GET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)
  li  t1, PRV_S
  bne t0, t1, jumpstart_smode_fail

  # Disable interrupts when switching modes to avoid clobbering any
  # state we set up if we encounter an interrupt.
  csrci sstatus, SSTATUS_SIE

  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd a0, A0_OFFSET_IN_SAVE_REGION(gp)
  sd a1, A1_OFFSET_IN_SAVE_REGION(gp)

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la a1, jump_to_function_in_umode
  csrw sepc, a1

  li t0, (PRV_S << SSTATUS_SPP_SHIFT)
  csrc sstatus, t0

  # Switch to the U-mode stack.
  GET_THREAD_ATTRIBUTES_HART_ID(t0)
  li  t1, (NUM_PAGES_PER_HART_FOR_UMODE_STACK * UMODE_STACK_PAGE_SIZE)
  mul t0, t0, t1
  la  t2, umode_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  li  t0, PRV_U
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)
  ld a1, A1_OFFSET_IN_SAVE_REGION(gp)

  sret

# Inputs:
#   a0: return status from U-mode function.
run_function_in_umode_return_point:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret
