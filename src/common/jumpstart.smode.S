# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.smode, "ax"

.global setup_smode
setup_smode:
  GET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)
  bnez  t0, setup_smode_done

  # This is the first time we're running S-mode.
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  jal enable_smode_float_and_vector_instructions

  jal setup_trap_vector

  jal setup_interrupt_enables

  jal setup_mmu_from_smode

  jal setup_heap

  jal setup_uart

  li t0, 1
  SET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

setup_smode_done:
  ret

.global enable_smode_float_and_vector_instructions
enable_smode_float_and_vector_instructions:
  li t0, (SSTATUS_FS | SSTATUS_VS)
  csrs sstatus, t0

  ret

.global setup_trap_vector
setup_trap_vector:
  la t0, stvec_trap_handler
  csrw stvec, t0

  ret

.global setup_interrupt_enables
setup_interrupt_enables:
  # Enable interrupts.
  li t0, SSTATUS_SIE | SSTATUS_SPP
  csrs sstatus, t0

  # Enable external interrupts.
  li t0, SIP_SEIP
  csrw sie, t0

  ret

# a0: address of target function.
# a1-a7: arguments to pass to the target function.
.global jump_to_function_in_smode
jump_to_function_in_smode:
  li  t0, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  # Save away the target function address and it's arguments.
  addi  sp, sp, -64
  sd    a0, 0(sp) # target function address.
  sd    a1, 8(sp) # target function arguments.
  sd    a2, 16(sp)
  sd    a3, 24(sp)
  sd    a4, 32(sp)
  sd    a5, 40(sp)
  sd    a6, 48(sp)
  sd    a7, 56(sp)

  jal setup_smode

  # Restore the target function address and it's arguments.
  ld    t0, 0(sp)
  # Function arguments have to be passed in a0-a6.
  ld    a0, 8(sp)
  ld    a1, 16(sp)
  ld    a2, 24(sp)
  ld    a3, 32(sp)
  ld    a4, 40(sp)
  ld    a5, 48(sp)
  ld    a6, 56(sp)
  addi  sp, sp, 64

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
  bexti gp, gp, SSTATUS_SPP_SHIFT
  beqz  gp, handle_trap_from_umode

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
  bexti gp, gp, SSTATUS_SPP_SHIFT
  beqz  gp, restore_umode_context

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

handle_syscall_run_func_in_umode_complete:
  # This is the return to supervisor path for run_function_in_umode().

  # Re-enable interrupts that were disabled in run_function_in_umode().
  # Set SPIE to 1, on sret this will set SIE to 1.
  li  t0, (PRV_S << SSTATUS_SPP_SHIFT) | SSTATUS_SPIE
  csrs  sstatus, t0

  la  t0, run_function_in_umode_return_point
  csrw sepc, t0

  # The return value from the umode function is in the umode
  # context saved for a0 when we took the ecall exception from umode to
  # smode. Place it in a0 smode context.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld t0, A0_OFFSET_IN_SAVE_REGION(gp)
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Restore S mode context from before the run_function_in_umode() call.
  RESTORE_ALL_GPRS

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

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la t0, jump_to_function_in_umode
  csrw sepc, t0

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

  sret

# Inputs:
#   a0: return status from U-mode function.
run_function_in_umode_return_point:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global just_wfi_from_smode
just_wfi_from_smode:
  wfi
  j just_wfi_from_smode
