# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

# This section should fall into the initial 4K page set up.
.section .jumpstart.text.mmode.init.enter, "ax"

.global _mmode_start
_mmode_start:
  la t0, mtvec_trap_handler
  csrw mtvec, t0

  csrr t0, mhartid

  li t1, MAX_NUM_HARTS_SUPPORTED
  bge t0, t1, just_wfi_from_mmode

  # Set up the stack.
  # S-mode and M-mode share the same stack.
  li  t1, (NUM_PAGES_PER_HART_FOR_SMODE_STACK * SMODE_STACK_PAGE_SIZE)
  mul t3, t0, t1
  la  t2, smode_stack_top
  add sp, t2, t3
  add sp, sp, t1 # We want the stack bottom.

  mv  fp, sp

  li t1, BATCH_MODE
  beqz t1, 1f

  # When running in batch mode, have the primary hart save away it's
  # return address.
  # This return address is common to all the harts and allows all
  # harts to exit back to where they came from.
  csrr t0, mhartid
  li t1, PRIMARY_HART_ID
  bne t0, t1, 1f
  la t1, batch_mode_exit_address
  sd ra, (t1)
  fence rw, rw
  la t1, batch_mode_exit_lock
  sd zero, (t1)

1:
  # The mmode init code is expected to fit in a 4KB page for Rivos internal
  # reasons.
  la t0, _JUMPSTART_TEXT_MMODE_INIT_BOUNDARY
  la t1, _JUMPSTART_TEXT_MMODE_INIT_ENTER_START
  sub t2, t0, t1
  li t3, 0x1000 # 4KB
  bgt t2, t3, jumpstart_mmode_fail

  # Run the setup_mmode before running any more code. Only the first
  # 4K page of mmode code is set up to run right now. setup_mmode()
  # will enable the rest of the mmode code.
  jal setup_mmode

  jal reset_csrs

  csrr  t0, mhartid

  # Check if this hart is in the active hart mask.
  li a0, ACTIVE_HART_MASK
  li t1, 1
  sll t1, t1, t0
  and a0, a0, t1
  bnez a0, 2f

  # Inactive hart.

  # If running in batch mode, return the inactive hart.
  li t2, BATCH_MODE
  bnez t2, batch_mode_return_unused_hart

  # Send the hart to WFI if not running in batch mode.
  j just_wfi_from_mmode

2:
  # Have the hart mark itself as running.
  la t1, hart_status_tracker
  add t1, t1, t0
  li t2, HART_RUNNING
  sb t2, 0(t1)

  mv a0, t0
  jal setup_thread_attributes_from_mmode

  # Enable interrupts in machine mode.
  li t0, MSTATUS_MIE
  csrs mstatus, t0
  li t0, MSTATUS_MPIE
  csrc mstatus, t0
  li t0, MIP_MEIP
  csrw mie, t0

  jal program_mstateen

  jal program_menvcfg

  jal enable_mmode_float_and_vector_instructions

  jal setup_smode_trap_delegation

  li  t0, ENABLE_VIRTUALIZATION
  beqz t0, 1f

  jal program_henvcfg

  jal setup_vsmode_trap_delegation

1:
  j jump_to_main

.section .jumpstart.text.mmode, "ax"

.global setup_smode_trap_delegation
setup_smode_trap_delegation:
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
            (1 << RISCV_EXCP_VS_ECALL) | \
            (1 << RISCV_EXCP_INST_PAGE_FAULT) | \
            (1 << RISCV_EXCP_LOAD_PAGE_FAULT) | \
            (1 << RISCV_EXCP_STORE_PAGE_FAULT) | \
            (1 << RISCV_EXCP_DATA_CORRUPTION_EXCEPTION) | \
            (1 << RISCV_EXCP_INST_GUEST_PAGE_FAULT) | \
            (1 << RISCV_EXCP_LOAD_GUEST_ACCESS_FAULT) | \
            (1 << RISCV_EXCP_VIRT_INSTRUCTION_FAULT) | \
            (1 << RISCV_EXCP_STORE_GUEST_AMO_ACCESS_FAULT)
  csrw medeleg, t0

  li t0, SIP_SEIP | SIP_STIP | SIP_SSIP | SIP_SGEIP
  csrw mideleg, t0

  ret

.global setup_vsmode_trap_delegation
setup_vsmode_trap_delegation:
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
  csrw hedeleg, t0

  # Delegate guest interrupts.
  li t0, MIP_VSEIP | MIP_VSTIP | MIP_VSSIP
  csrw hideleg, t0

  ret

.global program_henvcfg
program_henvcfg:
  # CBIE: Cache Block Invalidate instruction Enable
  # CBCFE: Cache Block Clean and Flush instruction Enable
  # CBZE: Cache Block Zero instruction Enable
  # PMBTE: Enables Svpbmt extension for S-mode and G-stage address translation.
  #        i.e., for page tables pointed to by satp or hgatp.
  li t0, (HENVCFG_CBIE | HENVCFG_CBCFE | HENVCFG_CBZE | HENVCFG_PBMTE)
  csrrs t1, henvcfg, t0

  ret

.global program_mstateen
program_mstateen:
  li t0, (SMSTATEEN0_HSCONTXT | SMSTATEEN0_IMSIC | SMSTATEEN0_AIA | SMSTATEEN0_SVSLCT | SMSTATEEN0_HSENVCFG | SMSTATEEN_STATEEN)
  csrw mstateen0, t0
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

.global reset_csrs
reset_csrs:
  csrw mcause, zero
  csrw mepc, zero
  csrw mie, zero
  csrw mip, zero
  MTIMER_RESET

  csrw satp, zero
  csrw scause, zero
  csrw sepc, zero
  csrw sie, zero
  csrw sip, zero
  csrw stvec, zero
  STIMER_RESET

  ret

.global enable_mmode_float_and_vector_instructions
enable_mmode_float_and_vector_instructions:
  li t0, (MSTATUS_VS | MSTATUS_FS)
  csrrs t1, mstatus, t0

  # Set vtype.vill=0 by running a dummy vsetvl instruction.
  # There are vector instructions (such as vmv1r.v) that
  # can run without running a vsetvl instruction first so we
  # need to make sure that the reset value of vill=1 has been cleared.
  vsetivli        zero, 8, e8, m1, ta, ma

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

  li t0, START_TEST_IN_MMODE
  bnez t0, jump_to_main_in_mmode

  jal delegate_mmode_resources_to_smode

  la a0, main
  jal run_function_in_smode

  j _mmode_end

# syscall handlers

handle_env_call_from_smode:
  # a7 will contain the syscall number

  li t0, SYSCALL_RUN_FUNC_IN_SMODE_COMPLETE
  beq a7, t0, handle_syscall_run_func_in_smode_complete

  j jumpstart_mmode_fail

handle_syscall_run_func_in_smode_complete:
  # This is the return to machine path for run_function_in_smode().

  # Re-enable interrupts that were disabled in run_function_in_smode().
  # Set MPIE to 1, on mret this will set MIE to 1.
  li  t0, (PRV_M << MSTATUS_MPP_SHIFT) | MSTATUS_MPIE
  csrs  mstatus, t0

  la  t0, run_function_in_smode_return_point
  csrw mepc, t0

  # Point to the address of the context save region we used when we
  # took the RUN_FUNC_IN_SMODE_COMPLETE syscall.
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES

  # The return value from the smode function is in the a0 location for smode
  # context saved when we took the ecall exception from smode to
  # mmode.
  ld t0, A0_OFFSET_IN_SAVE_REGION(gp)
  # Place it in the a0 location for the mmode context we saved before calling
  # run_function_in_smode().
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  sd t0, A0_OFFSET_IN_SAVE_REGION(gp)

  # Restore M mode context from before the run_function_in_smode() call.
  RESTORE_ALL_GPRS

  # This location is now free to be used by the next trap handler entry.
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # We've freed 2 context saves.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)
  addi gp, gp, 2
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)

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
  bne t0, t1, jumpstart_mmode_fail

  # Disable interrupts when switching modes to avoid clobbering any
  # state we set up if we encounter an interrupt. We will re-enable
  # the interrupts in the return path.
  csrci mstatus, MSTATUS_MIE

save_mmode_context_before_smode_function:
  # Make sure we have enough context saves remaining in M mode.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)
  beqz gp, jumpstart_mmode_fail

  addi gp, gp, -1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)

  # Save machine mode context
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  # Point to the address of the next context save region for the next
  # trap handler.
  addi gp, gp, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  MMODE_ROLE_DISABLE

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
  MMODE_ROLE_ENABLE

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

  # We don't currently expect mmode to handle a trap taken from VS mode.
  # Once we do the following code will need to be updated to save and restore
  # the V bit value across the trap handler.
  GET_THREAD_ATTRIBUTES_CURRENT_V_BIT(gp)
  bnez gp, jumpstart_mmode_fail

  # We just need to check MSB of MPP field here to determine if we came from
  # M or S mode. U mode is also handled in S mode path.
  csrr  gp, mstatus
  bexti gp, gp, MSTATUS_MPP_MSB
  bnez  gp, save_context

handle_trap_from_smode:
  MMODE_ROLE_ENABLE

save_context:
  # Make sure we have enough context saves remaining in M mode.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)
  beqz gp, jumpstart_mmode_fail

  addi gp, gp, -1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)

  # Save away the reg context of the mode we came from.
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  SAVE_ALL_GPRS

  csrr t0, mtval
  sd t0, TVAL_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, mepc
  sd t0, EPC_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, mstatus
  sd t0, STATUS_OFFSET_IN_SAVE_REGION(gp)

  csrr t0, hstatus
  sd t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)

  # Point to the address of the next context save region for the next
  # trap handler.
  addi gp, gp, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  # Check if the test has registered a trap handler for this trap.
  csrr  a0, mcause
  call  get_mmode_trap_handler_override

  beqz  a0, check_for_env_call_requests

  # Jump to the registered trap handler.
  # TODO: Do we need to pass any arguments to the trap handler?
  #       If so, we need to restore them from the context save region.
  jalr  ra, a0

restore_context:
  # Point to the address of the context save region we used when we
  # took the trap.
  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)
  addi gp, gp, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES

  ld t0, HSTATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw hstatus, t0

  ld t0, TVAL_OFFSET_IN_SAVE_REGION(gp)
  csrw mtval, t0

  ld t0, EPC_OFFSET_IN_SAVE_REGION(gp)
  csrw mepc, t0

  ld t0, STATUS_OFFSET_IN_SAVE_REGION(gp)
  csrw mstatus, t0

  bexti t0, t0, MSTATUS_MPP_MSB
  bnez  t0, restore_all_gprs

restore_smode_context:
  MMODE_ROLE_DISABLE

  li  t0, PRV_S
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

restore_all_gprs:
  RESTORE_ALL_GPRS

  # This location is now free to be used by the next trap handler entry.
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(gp)

  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)
  addi gp, gp, 1
  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(gp)

  csrr  gp, mscratch

  mret

check_for_env_call_requests:
  # We don't expect to get any env calls from M-mode at this time.
  csrr  t0, mstatus
  bexti t0, t0, MSTATUS_MPP_MSB
  bnez  t0, jumpstart_mmode_fail

  csrr  t0, mcause
  li  t1, RISCV_EXCP_S_ECALL
  beq t0, t1, handle_env_call_from_smode

  li  t1, RISCV_EXCP_VS_ECALL
  beq t0, t1, handle_env_call_from_smode

  j jumpstart_mmode_fail

.global get_mepc_for_current_exception
get_mepc_for_current_exception:
  # This should only be called from a registered exception handler.
  # Make sure that there is at least one exception we're handling at this point.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(t0)
  addi t0, t0, -MAX_NUM_CONTEXT_SAVES
  beqz t0, jumpstart_mmode_fail

  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t0)
  addi t0, t0, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  ld a0, EPC_OFFSET_IN_SAVE_REGION(t0)
  ret

# Inputs:
#  a0: mepc value to set.
.global set_mepc_for_current_exception
set_mepc_for_current_exception:
  # This should only be called from a registered exception handler.
  # Make sure that there is at least one exception we're handling at this point.
  GET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(t0)
  addi t0, t0, -MAX_NUM_CONTEXT_SAVES
  beqz t0, jumpstart_mmode_fail

  GET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t0)
  addi t0, t0, -REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES
  sd a0, EPC_OFFSET_IN_SAVE_REGION(t0)
  ret
