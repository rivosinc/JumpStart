# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.smode, "ax"

.global setup_smode
setup_smode:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  jal enable_smode_float_and_vector_instructions

  jal setup_smode_trap_vector

  jal setup_smode_interrupt_enables

  jal setup_mmu_from_smode

  jal setup_heap

  jal setup_uart

  li t0, 1
  SET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.global enable_smode_float_and_vector_instructions
enable_smode_float_and_vector_instructions:
  li t0, (SSTATUS_FS | SSTATUS_VS)
  csrs sstatus, t0

  ret

.global setup_smode_trap_vector
setup_smode_trap_vector:
  la t0, stvec_trap_handler
  csrw stvec, t0

  ret

.global setup_smode_interrupt_enables
setup_smode_interrupt_enables:
  # Enable interrupts.
  li t0, SSTATUS_SIE | SSTATUS_SPP
  csrs sstatus, t0

  # Enable external interrupts.
  li t0, SIP_SEIP
  csrw sie, t0

  ret

# Inputs:
#   a0: address of the function to run in usermode.
#   a1-a7 contains the arguments to pass to the user function.
.global run_function_in_vsmode
run_function_in_vsmode:
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

  # Make sure we have enough context saves remaining in S mode.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  beqz gp, jumpstart_smode_fail

  addi gp, gp, -1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  # Point to the address of the next context save region for the next
  # trap handler.
  addi gp, gp, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # Setup VS-mode in sstatus and hstatus. sepc will contain the address of
  # the function to run in VS-mode. Given we support single guest at the moment
  # we just set vgien to 1.
  li t0, HSTATUS_SPV
  li t1, 1 << HSTATUS_VGEIN_SHIFT
  or t0, t0, t1
  csrs hstatus, t0

  li t0, (SMSTATEEN0_IMSIC | SMSTATEEN0_AIA | SMSTATEEN0_SVSLCT)
  csrw hstateen0, t0

  li t0, SSTATUS_SPP
  csrs sstatus, t0

  la t0, jump_to_function_in_vsmode
  csrw sepc, t0

  sret

# Inputs:
#   a0: return status from VS-mode function.
run_function_in_vsmode_return_point:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# a0: address of target function.
# a1-a7: arguments to pass to the target function.
.global jump_to_function_in_smode
jump_to_function_in_smode:
  li  t0, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  GET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)
  bnez  t0, 1f

  # This is the first time we're running S-mode so we have to setup_smode().

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

  ld    a0, 0(sp) # target function address.
  ld    a1, 8(sp) # target function arguments.
  ld    a2, 16(sp)
  ld    a3, 24(sp)
  ld    a4, 32(sp)
  ld    a5, 40(sp)
  ld    a6, 48(sp)
  ld    a7, 56(sp)
  addi  sp, sp, 64

1:
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

.global exit_from_smode
exit_from_smode:
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

  # We could be coming from VS or VU mode. Clear the V bit.
  li  gp, 0
  SET_THREAD_ATTRIBUTES_CURRENT_V_BIT(gp)

  # Make sure we have enough context saves remaining in S mode.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  beqz gp, jumpstart_smode_fail

  addi gp, gp, -1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, hstatus
  sd t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, stval
  sd t0, TVAL_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, sepc
  sd t0, EPC_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, sstatus
  sd t0, STATUS_OFFSET_IN_SAVE_REGION(gp)

  # We just need to check the SPP field here to determine if we came from
  # S or U mode.
  bexti t0, t0, SSTATUS_SPP_SHIFT
  bnez  t0, 1f

  # We're handling a trap from umode.
  # Switch to the S-mode stack as we can't use the Umode stack.
  # We get the smode stack from the smode context that was saved
  # when we ran run_function_in_umode() - the context just prior to this.
  addi t0, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  ld sp, SP_OFFSET_IN_SAVE_REGION(t0)

1:
  # Point to the address of the next context save region for the next
  # trap handler.
  addi gp, gp, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

check_for_trap_handler_overrides:
  # Check if the test has registered a trap handler for this trap.
  csrr a0, scause
  call get_smode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

restore_context:
  # Point to the address of the context save region we used when we
  # took the trap.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES

  ld t0, TVAL_OFFSET_IN_SAVE_REGION(gp)
  csrw stval, t0

  ld t0, EPC_OFFSET_IN_SAVE_REGION(gp)
  csrw sepc, t0

  ld t0, STATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw sstatus, t0

  bexti t0, t0, SSTATUS_SPP_SHIFT
  beqz  t0, restore_umode_context

  ld t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw hstatus, t0

  j restore_all_gprs

restore_umode_context:
  li  t0, PRV_U
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

restore_all_gprs:
  RESTORE_ALL_GPRS

  # This location is now free to be used by the next trap handler entry.
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  addi gp, gp, 1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

# The return_from_stvec_trap_handler label is referenced in control transfer
# records diag so mark it as global.
.global return_from_stvec_trap_handler
return_from_stvec_trap_handler:
  sret

check_for_env_call_requests:
  csrr t0, scause
  li t1, RISCV_EXCP_U_ECALL
  beq t0, t1, handle_env_call_from_umode

  li t1, RISCV_EXCP_VS_ECALL
  beq t0, t1, handle_env_call_from_vsmode

  j jumpstart_smode_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_UMODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_umode_complete

  j jumpstart_smode_fail

handle_env_call_from_vsmode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_VSMODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_vsmode_complete

  j jumpstart_smode_fail

handle_syscall_run_func_in_umode_complete:
  # This is the return to supervisor path for run_function_in_umode().

  # Re-enable interrupts that were disabled in run_function_in_umode().
  # Set SPIE to 1, on sret this will set SIE to 1.
  li  t0, (PRV_S << SSTATUS_SPP_SHIFT) | SSTATUS_SPIE
  csrs  sstatus, t0

  la  t0, run_function_in_umode_return_point
  csrw sepc, t0

  # Point to the address of the context save region we used when we
  # took the RUN_FUNC_IN_UMODE_COMPLETE syscall.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES

  # The return value from the umode function is in the umode
  # context saved for a0 when we took the ecall exception from umode to
  # smode.
  ld t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Place it in the a0 location for the mmode context we saved before calling
  # run_function_in_umode().
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  sd t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Restore S mode context from before the run_function_in_umode() call.
  RESTORE_ALL_GPRS

  # This location is now free to be used by the next trap handler entry.
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # We've freed 2 context saves.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  addi gp, gp, 2
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

  sret

handle_syscall_run_func_in_vsmode_complete:
  # This is the return to supervisor path for run_function_in_vsmode().

  # Re-enable interrupts that were disabled in run_function_in_vsmode().
  # Set SPIE to 1, on sret this will set SIE to 1.
  li  t0, (PRV_S << SSTATUS_SPP_SHIFT) | SSTATUS_SPIE
  csrs  sstatus, t0

  li t0, HSTATUS_SPV
  csrc hstatus, t0

  la  t0, run_function_in_vsmode_return_point
  csrw sepc, t0

  # Point to the address of the context save region we used when we
  # took the RUN_FUNC_IN_VSMODE_COMPLETE syscall.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES

  # The return value from the vsmode function is in the vsmode
  # context saved for a0 when we took the ecall exception from vsmode to
  # smode.
  ld t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Place it in the a0 location for the mmode context we saved before calling
  # run_function_in_vsmode().
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  sd t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Restore S mode context from before the run_function_in_vsmode() call.
  RESTORE_ALL_GPRS

  # This location is now free to be used by the next trap handler entry.
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # We've freed 2 context saves.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  addi gp, gp, 2
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

  sret

# Inputs:
#   a0: address of the function to run in usermode.
#   a1-a7 contains the arguments to pass to the user function.
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

  # Make sure we have enough context saves remaining in S mode.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)
  beqz gp, jumpstart_smode_fail

  addi gp, gp, -1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(gp)

  # Save S-mode context
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  # Point to the address of the next context save region for the next
  # trap handler.
  addi gp, gp, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
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

  la t0, jump_to_function_in_umode
  csrw sepc, t0

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


.global get_sepc_for_current_exception
get_sepc_for_current_exception:
  # This should only be called from a registered exception handler.
  # Make sure that there is at least one exception we're handling at this point.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(t0)
  addi t0, t0, -MAX_NUM_CONTEXT_SAVES
  beqz t0, jumpstart_smode_fail

  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t0)
  addi t0, t0, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  ld a0, EPC_OFFSET_IN_SAVE_REGION(t0)
  ret

# Inputs:
#  a0: sepc value to set.
.global set_sepc_for_current_exception
set_sepc_for_current_exception:
  # This should only be called from a registered exception handler.
  # Make sure that there is at least one exception we're handling at this point.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(t0)
  addi t0, t0, -MAX_NUM_CONTEXT_SAVES
  beqz t0, jumpstart_smode_fail

  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t0)
  addi t0, t0, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  sd a0, EPC_OFFSET_IN_SAVE_REGION(t0)
  ret
