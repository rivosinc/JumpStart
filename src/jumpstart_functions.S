# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.supervisor, "ax"

# a0 contains the address of the function to jump to.
.global jump_to_function_in_smode
jump_to_function_in_smode:
  li  t0, SUPERVISOR_MODE_ENCODING
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
  li  gp, SUPERVISOR_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)

  csrr  gp, sstatus
  srli  gp, gp, MSTATUS_SPP_SHIFT
  andi  gp, gp, MSTATUS_SPP_MASK
  addi  gp, gp, -SUPERVISOR_MODE_ENCODING
  beqz  gp, handle_trap_from_supervisor_mode
  j  handle_trap_from_user_mode

handle_trap_from_supervisor_mode:
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  j save_context

handle_trap_from_user_mode:
  # Save away the U-mode stack.
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  sd sp, SP_OFFSET_IN_SAVE_REGION(gp)
  # and switch to the S-mode stack as we can't use the Umode stack.
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(sp)
  ld sp, SP_OFFSET_IN_SAVE_REGION(sp)

  # We will save away the user mode context to the user mode region
  # which GP currently points to.

save_context:
  SAVE_ALL_GPRS

  # Check if the test has registered a trap handler for this trap.
  csrr a0, scause
  call get_supervisor_mode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

  csrr  gp, sstatus
  srli  gp, gp, MSTATUS_SPP_SHIFT
  andi  gp, gp, MSTATUS_SPP_MASK
  addi  gp, gp, -SUPERVISOR_MODE_ENCODING
  bnez  gp, return_from_handling_user_mode_trap

  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  j restore_context

return_from_handling_user_mode_trap:
  li  gp, USER_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)
  GET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

restore_context:
  RESTORE_ALL_GPRS

  sret

check_for_env_call_requests:
  csrr t0, scause
  li t1, SCAUSE_EC_ENV_CALL_FROM_UMODE
  beq t0, t1, handle_env_call_from_umode

  j jumpstart_supervisor_fail

handle_env_call_from_umode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_user_mode_complete

  j jumpstart_supervisor_fail

.global jumpstart_supervisor_fail
jumpstart_supervisor_fail:
  # TODO: This is a temporary fail handler. We need to figure out
  wfi

handle_syscall_run_func_in_user_mode_complete:
  # This is the return to supervisor path for run_function_in_user_mode().

  # Restore S mode context and return status in a0
  GET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  ld a1, SSTATUS_OFFSET_IN_SAVE_REGION(gp)
  li a2, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
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
  li  t1, SUPERVISOR_MODE_ENCODING
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

.global sync_all_harts_from_supervisor_mode
sync_all_harts_from_supervisor_mode:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_attributes_hart_id_from_supervisor_mode

  li t0, 1
  sll t2, t0, a0

  la t1, hart_sync_point

  amoor.w.aq t3, t2, (t1)

  slli t0, t0, PRIMARY_HART_ID
  bne t0, t2, wait_for_primary_hart_to_clear_sync_point_bits

  jal get_active_hart_mask_from_supervisor_mode

wait_for_all_harts_to_set_sync_point_bits:
  # Primary hart waits till all the harts have set their bits in the sync point.
  lw t0, (t1)
  bne t0, a0, wait_for_all_harts_to_set_sync_point_bits

  amoswap.w t0, zero, (t1)

  bne t0, a0, jumpstart_supervisor_fail

  j return_from_sync_all_harts_from_supervisor_mode

wait_for_primary_hart_to_clear_sync_point_bits:
  # non-primary harts wait for the primary hart to clear the sync point bits.
  lw t0, (t1)
  srl t0, t0, a0
  andi t0, t0, 1
  bnez t0, wait_for_primary_hart_to_clear_sync_point_bits

return_from_sync_all_harts_from_supervisor_mode:
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
  li  a7, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  ecall

  # We shouldn't come back here.
  wfi


.section .jumpstart.data.privileged, "aw"

.global hart_status_tracker
hart_status_tracker:
  .rept MAX_NUM_HARTS_SUPPORTED
    .byte HART_INACTIVE
  .endr


.align 2
.global hart_sync_point
hart_sync_point:
  # We're going to use the amoor.w instruction to update the bits
  # so allocate 4 bytes.
  .4byte 0x0
