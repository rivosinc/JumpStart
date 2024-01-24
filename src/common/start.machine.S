# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

# This section should fall into the initial 4K page set up.
.section .jumpstart.text.machine.init, "ax"

.global _machine_mode_start
_machine_mode_start:
  la t0, mtvec_trap_handler
  csrw mtvec, t0

  csrr  t0, mhartid

  # Make sure that this hart should be active.
  jal get_active_hart_mask_from_machine_mode
  li t1, 1
  sll t1, t1, t0
  and a0, a0, t1
  # We don't know about this core. Move it to the wfi state
  beqz a0, just_wfi

  # Have the hart mark itself as running.
  la t1, hart_status_tracker
  add t1, t1, t0
  li t2, HART_RUNNING
  sb t2, 0(t1)

  # S-mode and M-mode share the same stack.
  li  t1, (NUM_PAGES_PER_HART_FOR_SUPERVISOR_STACK * SUPERVISOR_STACK_PAGE_SIZE)
  mul t0, t0, t1
  la  t2, supervisor_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  mv  fp, sp

  # Enable interrupts in machine mode.
  li t0, MSTATUS_MIE
  csrs mstatus, t0
  li t0, MIP_MEIP
  csrw mie, t0

  jal setup_thread_attributes

  jal program_menvcfg

  jal enable_float_and_vector_instructions

  jal setup_supervisor_mode_trap_related_csrs

  jal enable_mmu_from_machine_mode

  jal setup_heap

  jal setup_uart

  j jump_to_main

.section .jumpstart.text.machine, "ax"

.global setup_supervisor_mode_trap_related_csrs
setup_supervisor_mode_trap_related_csrs:
  la t0, stvec_trap_handler
  csrw stvec, t0

  # Enable trap delegation to supervisor mode.
  li t0, (1 << RISCV_EXCP_INST_ADDR_MIS) | \
            (1 << RISCV_EXCP_INST_ACCESS_FAULT) | \
            (1 << RISCV_EXCP_ILLEGAL_INST) | \
            (1 << RISCV_EXCP_BREAKPOINT) | \
            (1 << RISCV_EXCP_LOAD_ADDR_MIS) | \
            (1 << RISCV_EXCP_LOAD_ACCESS_FAULT) | \
            (1 << RISCV_EXCP_STORE_AMO_ADDR_MIS) | \
            (1 << RISCV_EXCP_STORE_AMO_ACCESS_FAULT) | \
            (1 << RISCV_EXCP_U_ECALL) | \
            (1 << RISCV_EXCP_INST_PAGE_FAULT) | \
            (1 << RISCV_EXCP_LOAD_PAGE_FAULT) | \
            (1 << RISCV_EXCP_STORE_PAGE_FAULT)
  csrw medeleg, t0

  li t0, SIP_SEIP | SIP_STIP | SIP_SSIP
  csrw mideleg, t0

  # Enable interrupts in supervisor mode. Indicate that we're executing
  # in a privileged mode before entering Supervisor mode.
  li t0, SSTATUS_SIE | SSTATUS_SPP
  csrs sstatus, t0

  # Enable external interrupts in supervisor mode.
  li t0, SIP_SEIP
  csrw sie, t0

  ret

.global setup_thread_attributes
setup_thread_attributes:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  csrr a0, mhartid
  li t1, MAX_NUM_HARTS_SUPPORTED
  bgeu a0, t1, jumpstart_machine_fail

  li  t2, THREAD_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t2, a0, t2
  la  t1, thread_attributes_region
  add tp, t1, t2

  SET_THREAD_ATTRIBUTES_HART_ID(a0)

  li t0, TRAP_OVERRIDE_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t0, a0, t0
  la t1, trap_override_attributes_region
  add t0, t1, t0
  SET_THREAD_ATTRIBUTES_TRAP_OVERRIDE_STRUCT_ADDRESS(t0)

  li t0, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  mul t0, a0, t0

  la t1, mmode_reg_context_save_region
  add t1, t1, t0
  la t2, mmode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_machine_fail
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  la t1, lower_mode_in_mmode_reg_context_save_region
  add t1, t1, t0
  la t2, lower_mode_in_mmode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_machine_fail
  SET_THREAD_ATTRIBUTES_LOWER_MODE_IN_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  la t1, smode_reg_context_save_region
  add t1, t1, t0
  la t2, smode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_machine_fail
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  la t1, umode_reg_context_save_region
  add t1, t1, t0
  la t2, umode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_machine_fail
  SET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  li  t0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE
  SET_THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER(t0)

  li  t0, PRV_M
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.global program_menvcfg
program_menvcfg:
  # CBIE: Cache Block Invalidate instruction Enable
  # CBCFE: Cache Block Clean and Flush instruction Enable
  # CBZE: Cache Block Zero instruction Enable
  # PMBTE: Enables Svpbmt extension for S-mode and G-stage address translation.
  #        i.e., for page tables pointed to by satp or hgatp.
  # CDE: Counter Delegation Enable
  li t0, (MENVCFG_CBIE | MENVCFG_CBCFE | MENVCFG_CBZE | MENVCFG_PBMTE | MENVCFG_CDE)
  csrrs t1, menvcfg, t0

  ret

.global enable_float_and_vector_instructions
enable_float_and_vector_instructions:
  li t0, (MSTATUS_VS | MSTATUS_FS)
  csrrs t1, mstatus, t0

  ret

.global delegate_mmode_resources_to_smode
delegate_mmode_resources_to_smode:
  # Delegate resources which are otherwise retained by M mode.

  # Allow S mode to handle PMU overflow interrupts.
  li t0, 1 << IRQ_PMU_OVF
  csrs mideleg, t0

  # Enable access to all 32 counters from S mode.
  li t0, 0xFFFFFFFF
  csrw mcounteren, t0

  ret

.global jump_to_main
jump_to_main:

  jal start_test_in_machine_mode
  bnez a0, jump_to_main_in_machine_mode

  jal delegate_mmode_resources_to_smode

  la a0, main
  jal run_function_in_smode

  j _machine_mode_end

# syscall handlers

handle_env_call_from_smode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_SUPERVISOR_MODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_supervisor_mode_complete

  j jumpstart_machine_fail

handle_syscall_run_func_in_supervisor_mode_complete:
  # This is the return to machine path for run_function_in_smode().

  # Re-enable interrupts that were disabled in run_function_in_smode().
  # Set MPIE to 1, on mret this will set MIE to 1.
  li  t0, (PRV_M << MSTATUS_MPP_SHIFT) | MSTATUS_MPIE
  csrs  mstatus, t0

  la  t0, run_function_in_smode_return_point
  csrw mepc, t0

  # Restore M mode context
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  RESTORE_ALL_GPRS

  # return status is in a0.
  GET_THREAD_ATTRIBUTES_LOWER_MODE_IN_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  ld a0, A0_OFFSET_IN_SAVE_REGION(gp)

  mret

# END syscall handlers

# a0 contains the address of the function to run in supervisor mode.
# a1-a7 contains the arguments to pass to the supervisor function.
.global run_function_in_smode
run_function_in_smode:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  GET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)
  li  t1, PRV_M
  bne t0, t1, jumpstart_machine_fail

  # Disable interrupts when switching modes to avoid clobbering any
  # state we set up if we encounter an interrupt. We will re-enable
  # the interrupts in the return path.
  csrci mstatus, MSTATUS_MIE

  # Save machine mode context
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  li  t0, MSTATUS_MPP
  csrc mstatus, t0
  li  t0, (PRV_S << MSTATUS_MPP_SHIFT)
  csrs  mstatus, t0

  la t0, jump_to_function_in_smode
  csrw mepc, t0

  mret

# Inputs:
#   a0: return status from S-mode function.
run_function_in_smode_return_point:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

# The mtvec.base must always be 4 byte aligned.
.align 2
.global mtvec_trap_handler
mtvec_trap_handler:
  # Save away gp as we may be entering the mmode trap handler when running
  # the smode trap handler.
  csrw mscratch, gp

  li  gp, PRV_M
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)

  # We just need to check MSB of MPP field here to determine if we came from
  # M or S mode. U mode is also handled in S mode path.
  csrr  gp, mstatus
  bexti gp, gp, MSTATUS_MPP_MSB
  bnez  gp, handle_trap_from_machine_mode

handle_trap_from_supervisor_mode:
  # Save away the S/U-mode reg context.
  GET_THREAD_ATTRIBUTES_LOWER_MODE_IN_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  j save_context

handle_trap_from_machine_mode:
  # Save away the M-mode reg context.
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

save_context:
  SAVE_ALL_GPRS

  csrr t0, hstatus
  sd t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)

  # Check if the test has registered a trap handler for this trap.
  csrr  a0, mcause
  call  get_machine_mode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

  csrr  gp, mstatus
  bexti gp, gp, MSTATUS_MPP_MSB
  bnez  gp, restore_machine_mode_context

restore_supervisor_mode_context:
  # Set thread attribute from mstatus.
  csrr  gp, mstatus
  bexti gp, gp, MSTATUS_MPP_SHIFT
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(gp)

  GET_THREAD_ATTRIBUTES_LOWER_MODE_IN_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  j restore_context

restore_machine_mode_context:
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

restore_context:
  ld t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw hstatus, t0

  RESTORE_ALL_GPRS
  csrr  gp, mscratch

  mret

check_for_env_call_requests:
  # We don't expect to get any env calls from M-mode at this time.
  csrr  t0, mstatus
  bexti t0, t0, MSTATUS_MPP_MSB
  bnez  t0, jumpstart_machine_fail

  csrr  t0, mcause
  li  t1, RISCV_EXCP_S_ECALL
  beq t0, t1, handle_env_call_from_smode

  j jumpstart_machine_fail
