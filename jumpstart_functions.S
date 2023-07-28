# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

# NOTE: This macro does not save a0. It must be handled by macro user.
#define SAVE_ALL_GPRS     ;\
  sd sp, SP_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s0, S0_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s1, S1_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s2, S2_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s3, S3_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s4, S4_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s5, S5_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s6, S6_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s7, S7_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s8, S8_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s9, S9_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd s10, S10_OFFSET_IN_SAVE_REGION(a0)  ;\
  sd s11, S11_OFFSET_IN_SAVE_REGION(a0)  ;\
  sd t0, T0_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t1, T1_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t2, T2_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t3, T3_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t4, T4_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t5, T5_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd t6, T6_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a1, A1_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a2, A2_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a3, A3_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a4, A4_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a5, A5_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a6, A6_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd a7, A7_OFFSET_IN_SAVE_REGION(a0)    ;\
  sd ra, RA_OFFSET_IN_SAVE_REGION(a0)

#define RESTORE_ALL_GPRS  ;\
  ld sp, SP_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s0, S0_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s1, S1_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s2, S2_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s3, S3_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s4, S4_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s5, S5_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s6, S6_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s7, S7_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s8, S8_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s9, S9_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld s10, S10_OFFSET_IN_SAVE_REGION(a0)  ;\
  ld s11, S11_OFFSET_IN_SAVE_REGION(a0)  ;\
  ld t0, T0_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t1, T1_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t2, T2_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t3, T3_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t4, T4_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t5, T5_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld t6, T6_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a1, A1_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a2, A2_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a3, A3_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a4, A4_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a5, A5_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a6, A6_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a7, A7_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld ra, RA_OFFSET_IN_SAVE_REGION(a0)    ;\
  ld a0, A0_OFFSET_IN_SAVE_REGION(a0)

.section .jumpstart.text.supervisor, "ax"

.global jump_to_main_in_supervisor_mode
jump_to_main_in_supervisor_mode:
  la t0, stvec_trap_handler
  csrw stvec, t0

  li  a0, SUPERVISOR_MODE_ENCODING
  call set_thread_attributes_current_mode_from_supervisor_mode

  li a0, (1 << SIE_EXT_INTERRUPT)
  csrw sie, a0

  li a0, (1 << SSTATUS_SIE_SHIFT) | (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  csrs sstatus, a0

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

  # We are in S-mode handling a trap from S-mode.
  # Point a0 to the S-mode reg context save region.
  la a0, smode_reg_context_save_region
  j save_context

1:
  # We are in S-mode handling a trap from U-mode.
  # Point a0 to the U-mode reg context save region.

  # Save away the U-mode stack.
  la a0, umode_reg_context_save_region
  sd sp, SP_OFFSET_IN_SAVE_REGION(a0)
  # and switch to the S-mode stack as we can't use the Umode stack.
  la sp, smode_reg_context_save_region
  ld sp, SP_OFFSET_IN_SAVE_REGION(sp)

save_context:
  SAVE_ALL_GPRS

  # Save away the a0 passed to us when entering the trap handler to the
  # appropriate reg context save region we've chosen above.
  csrr t0, sscratch
  sd t0, A0_OFFSET_IN_SAVE_REGION(a0)

  # Change current mode to S.
  li  a0, SUPERVISOR_MODE_ENCODING
  jal set_thread_attributes_current_mode_from_supervisor_mode

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
  la a0, smode_reg_context_save_region
  j restore_context

switch_to_umode_stack:
  li  a0, USER_MODE_ENCODING
  jal set_thread_attributes_current_mode_from_supervisor_mode
  la a0, umode_reg_context_save_region
  ld sp, SP_OFFSET_IN_SAVE_REGION(a0)

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
  la a0, smode_reg_context_save_region
  ld a1, SEPC_OFFSET_IN_SAVE_REGION(a0)
  csrw sepc, a1

  ld a1, SSTATUS_OFFSET_IN_SAVE_REGION(a0)
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
  la a1, umode_reg_context_save_region
  sd a0, A0_OFFSET_IN_SAVE_REGION(a1)

  jal get_thread_attributes_current_mode_from_supervisor_mode

  li  t1, SUPERVISOR_MODE_ENCODING
  bne a0, t1, jumpstart_supervisor_fail

  # Save S-mode context
  la a0, smode_reg_context_save_region
  SAVE_ALL_GPRS

  csrr t0, sstatus
  sd t0, SSTATUS_OFFSET_IN_SAVE_REGION(a0)

  la  t0, smode_return
  sd t0, SEPC_OFFSET_IN_SAVE_REGION(a0)

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la a1, jump_to_function_in_umode
  csrw sepc, a1

  li t0, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  csrc sstatus, t0

  li  a0, USER_MODE_ENCODING
  jal set_thread_attributes_current_mode_from_supervisor_mode

  la a0, umode_reg_context_save_region
  ld a0, A0_OFFSET_IN_SAVE_REGION(a0)

  sret

smode_return:
  # Usermode return status using a0. Given umode returns through ecall, we save
  # a0 to umode_reg_context_save_region in ecall handler and return to this point to continue
  # s-mode execution from the place we left it.
  la a0, umode_reg_context_save_region
  ld a0, A0_OFFSET_IN_SAVE_REGION(a0)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# User mode code. Don't add any supervisor mode code in this section.
.section .jumpstart.text.umode, "ax"

# A0 contains the address of the function to jump to.
.global jump_to_function_in_umode
jump_to_function_in_umode:
  la sp, umode_stack_bottom

  # A0 contains arg value passed by S mode.
  jalr ra, a0

  # a0 contains the exit code.
  li  a7, SYSCALL_RETURN_TO_SUPERVISOR_MODE
  ecall

  # We shouldn't come back here.
  wfi
