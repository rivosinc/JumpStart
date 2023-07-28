# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

#define RA_OFFSET  (0 * 8)
#define SP_OFFSET  (1 * 8)
#define GP_OFFSET  (2 * 8)
#define T0_OFFSET  (4 * 8)
#define T1_OFFSET  (5 * 8)
#define T2_OFFSET  (6 * 8)
#define S0_OFFSET  (7 * 8)
#define S1_OFFSET  (8 * 8)
#define A0_OFFSET  (9 * 8)
#define A1_OFFSET  (10 * 8)
#define A2_OFFSET  (11 * 8)
#define A3_OFFSET  (12 * 8)
#define A4_OFFSET  (13 * 8)
#define A5_OFFSET  (14 * 8)
#define A6_OFFSET  (15 * 8)
#define A7_OFFSET  (16 * 8)
#define S2_OFFSET  (17 * 8)
#define S3_OFFSET  (18 * 8)
#define S4_OFFSET  (19 * 8)
#define S5_OFFSET  (20 * 8)
#define S6_OFFSET  (21 * 8)
#define S7_OFFSET  (22 * 8)
#define S8_OFFSET  (23 * 8)
#define S9_OFFSET  (24 * 8)
#define S10_OFFSET  (25 * 8)
#define S11_OFFSET  (26 * 8)
#define T3_OFFSET  (27 * 8)
#define T4_OFFSET  (28 * 8)
#define T5_OFFSET  (29 * 8)
#define T6_OFFSET  (30 * 8)
#define SEPC_OFFSET  (31 * 8)
#define SSTATUS_OFFSET  (32 * 8)

# Note: These macros don't touch a0, it must be handled by macro user.

#define SAVE_CALLEE_SAVED ;\
  sd sp, SP_OFFSET(a0)    ;\
  sd gp, GP_OFFSET(a0)    ;\
  sd s0, S0_OFFSET(a0)    ;\
  sd s1, S1_OFFSET(a0)    ;\
  sd s2, S2_OFFSET(a0)    ;\
  sd s3, S3_OFFSET(a0)    ;\
  sd s4, S4_OFFSET(a0)    ;\
  sd s5, S5_OFFSET(a0)    ;\
  sd s6, S6_OFFSET(a0)    ;\
  sd s7, S7_OFFSET(a0)    ;\
  sd s8, S8_OFFSET(a0)    ;\
  sd s9, S9_OFFSET(a0)    ;\
  sd s10, S10_OFFSET(a0)    ;\
  sd s11, S11_OFFSET(a0)

#define SAVE_CALLER_SAVED ;\
  sd t0, T0_OFFSET(a0)    ;\
  sd t1, T1_OFFSET(a0)    ;\
  sd t2, T2_OFFSET(a0)    ;\
  sd t3, T3_OFFSET(a0)    ;\
  sd t4, T4_OFFSET(a0)    ;\
  sd t5, T5_OFFSET(a0)    ;\
  sd t6, T6_OFFSET(a0)    ;\
  sd a1, A1_OFFSET(a0)    ;\
  sd a2, A2_OFFSET(a0)    ;\
  sd a3, A3_OFFSET(a0)    ;\
  sd a4, A4_OFFSET(a0)    ;\
  sd a5, A5_OFFSET(a0)    ;\
  sd a6, A6_OFFSET(a0)    ;\
  sd a7, A7_OFFSET(a0)    ;\
  sd ra, RA_OFFSET(a0)

#define RESTORE_CALLEE_SAVED ;\
  ld sp, SP_OFFSET(a0)    ;\
  ld gp, GP_OFFSET(a0)    ;\
  ld s0, S0_OFFSET(a0)    ;\
  ld s1, S1_OFFSET(a0)    ;\
  ld s2, S2_OFFSET(a0)    ;\
  ld s3, S3_OFFSET(a0)    ;\
  ld s4, S4_OFFSET(a0)    ;\
  ld s5, S5_OFFSET(a0)    ;\
  ld s6, S6_OFFSET(a0)    ;\
  ld s7, S7_OFFSET(a0)    ;\
  ld s8, S8_OFFSET(a0)    ;\
  ld s9, S9_OFFSET(a0)    ;\
  ld s10, S10_OFFSET(a0)    ;\
  ld s11, S11_OFFSET(a0)

#define RESTORE_CALLER_SAVED ;\
  ld t0, T0_OFFSET(a0)       ;\
  ld t1, T1_OFFSET(a0)       ;\
  ld t2, T2_OFFSET(a0)       ;\
  ld t3, T3_OFFSET(a0)       ;\
  ld t4, T4_OFFSET(a0)       ;\
  ld t5, T5_OFFSET(a0)       ;\
  ld t6, T6_OFFSET(a0)       ;\
  ld a1, A1_OFFSET(a0)       ;\
  ld a2, A2_OFFSET(a0)       ;\
  ld a3, A3_OFFSET(a0)       ;\
  ld a4, A4_OFFSET(a0)       ;\
  ld a5, A5_OFFSET(a0)       ;\
  ld a6, A6_OFFSET(a0)       ;\
  ld a7, A7_OFFSET(a0)       ;\
  ld ra, RA_OFFSET(a0)

.section .jumpstart.data.privileged, "aw"

.global smode_reg_context_save_region
smode_reg_context_save_region:
.rep 33
  .8byte 0x0000000000000000
.endr

.global umode_reg_context_save_region
umode_reg_context_save_region:
.rep 33
  .8byte 0x0000000000000000
.endr

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
  beqz a0, switch_to_smode_stack
  la a0, smode_reg_context_save_region
  j save_context

switch_to_smode_stack:
  # We are in S-mode handling a trap from U-mode so switch to the
  # S-mode stack.

  # Save away the U-mode stack.
  la a0, umode_reg_context_save_region
  sd sp, SP_OFFSET(a0)

  la sp, smode_reg_context_save_region
  ld sp, SP_OFFSET(sp)

save_context:
  SAVE_CALLER_SAVED

  # Save away the a0 passed to us when entering the trap handler.
  csrr t0, sscratch
  sd t0, A0_OFFSET(a0)

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
  ld sp, SP_OFFSET(a0)

restore_context:
  RESTORE_CALLER_SAVED
  ld a0, A0_OFFSET(a0)

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
  ld a1, SEPC_OFFSET(a0)
  csrw sepc, a1

  ld a1, SSTATUS_OFFSET(a0)
  li a2, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  or a1, a1, a2
  csrw sstatus, a1

  RESTORE_CALLEE_SAVED
  RESTORE_CALLER_SAVED

  ld a0, A0_OFFSET(a0)
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
  sd a0, A0_OFFSET(a1)

  jal get_thread_attributes_current_mode_from_supervisor_mode

  li  t1, SUPERVISOR_MODE_ENCODING
  bne a0, t1, jumpstart_supervisor_fail

  # Save S-mode context
  la a0, smode_reg_context_save_region
  SAVE_CALLEE_SAVED
  SAVE_CALLER_SAVED

  csrr t0, sstatus
  sd t0, SSTATUS_OFFSET(a0)

  la  t0, smode_return
  sd t0, SEPC_OFFSET(a0)

  # Load U-mode context. We just need to set sepc, sstatus and a0 register.
  la a1, jump_to_function_in_umode
  csrw sepc, a1

  li t0, (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  csrc sstatus, t0

  li  a0, USER_MODE_ENCODING
  jal set_thread_attributes_current_mode_from_supervisor_mode

  la a0, umode_reg_context_save_region
  ld a0, A0_OFFSET(a0)

  sret

smode_return:
  # Usermode return status using a0. Given umode returns through ecall, we save
  # a0 to umode_reg_context_save_region in ecall handler and return to this point to continue
  # s-mode execution from the place we left it.
  la a0, umode_reg_context_save_region
  ld a0, A0_OFFSET(a0)

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
