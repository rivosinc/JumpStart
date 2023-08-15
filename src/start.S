# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.rcode.init, "ax"
.global _rcode_start
_rcode_start:
  la t0, _rtvec
  csrw rtvec, t0

  jal update_mcrr_0_to_cover_jumpstart_machine_code

  jal setup_pmarr

  la    t0, _machine_start
  csrw repc, t0
  rret

.org 512
_rtvec:
  wfi

.section .jumpstart.text.rcode, "ax"

update_mcrr_0_to_cover_jumpstart_machine_code:
  # The reset default of the MCRR_0 is the 4K page starting at the LLC-as-SRAM
  # range base address. We expect _machine_start to be at the beginning of this page.
  # Update the MCRR_0 to include all the machine mode code pages for the
  # jumpstart framework.

  la t0, _machine_start
  csrw mcrr_0_base, t0

  # Determine the size of the jumpstart machine mode code region.
  # We expect it to start at _machine_start (from the .jumpstart.machine.init) section
  # and extend to jumpstart_machine_mode_end_point (from the
  # from the .jumpstart.machine.end
  la t1, jumpstart_machine_mode_end_point
  sub t0, t1, t0

  # Compute the mask for the number of machine mode code pages.
  addi t0, t0, -1
  not t0, t0
  ori t0, t0, 0x1
  csrw mcrr_0_mask, t0

  ret

# This section should fall into the initial 4K page set up in MCRR_0
.section .jumpstart.text.machine.init, "ax"

.global _machine_start
_machine_start:
  la t0, mtvec_trap_handler
  csrw mtvec, t0

  csrr  t0, mhartid

  # Make sure that this hart should be active.
  jal get_active_hart_mask_from_machine_mode
  li t1, 1
  sll t1, t1, t0
  and a0, a0, t1
  beqz a0, jumpstart_fail

  # Have the hart mark itself as running.
  la t1, hart_status_tracker
  add t1, t1, t0
  li t2, HART_RUNNING
  sb t2, 0(t1)

  # Set up the stack for M-mode and S-mode.
  li  t1, (NUM_PAGES_PER_HART_FOR_PRIVILEGED_STACK * 4096)
  mul t0, t0, t1
  la  t2, privileged_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  mv  fp, sp

  jal setup_thread_attributes

  jal enable_svpbmt_for_supervisor_mode

  jal setup_supervisor_mode_trap_related_csrs

  jal enable_mmu_from_machine_mode

  j jump_to_main

.section .jumpstart.text.machine, "ax"

.global setup_supervisor_mode_trap_related_csrs
setup_supervisor_mode_trap_related_csrs:
  la t0, stvec_trap_handler
  csrw stvec, t0

  # Enable trap delegation to supervisor mode.
  li t0, (1 << SCAUSE_EC_ENV_CALL_FROM_UMODE) | (1 << SCAUSE_EC_ILLEGAL_INSTRUCTION)
  csrw medeleg, t0
  li t0, (1 << MIDELEG_S_SOFT_INTERRUPT) | (1 << MIDELEG_S_TIMER_INTERRUPT) | (1 << MIDELEG_S_EXT_INTERRUPT)
  csrw mideleg, t0

  # Enable interrupts in supervisor mode. Indicate that we're executing
  # in a privileged mode before entering Supervisor mode.
  li t0, (1 << SSTATUS_SIE_SHIFT) | (SUPERVISOR_MODE_ENCODING << MSTATUS_SPP_SHIFT)
  csrs sstatus, t0

  # Enable external interrupts in supervisor mode.
  li t0, (1 << SIE_EXT_INTERRUPT)
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
  bgeu a0, t1, jumpstart_fail

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
  bgeu t1, t2, jumpstart_fail
  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  la t1, smode_reg_context_save_region
  add t1, t1, t0
  la t2, smode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_fail
  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  la t1, umode_reg_context_save_region
  add t1, t1, t0
  la t2, umode_reg_context_save_region_end
  bgeu t1, t2, jumpstart_fail
  SET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)

  li  t0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE
  SET_THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER(t0)

  li  t0, MACHINE_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret


.global enable_svpbmt_for_supervisor_mode
enable_svpbmt_for_supervisor_mode:
  # Enable menvcfg.pbmte
  # The PBMTE bit controls whether the Svpbmt extension is
  # available for use in S-mode and G-stage address translation
  # (i.e., for page tables pointed to by satp or hgatp).
  csrr  t0, menvcfg
  li  t1, (1 << MENVCFG_PBMTE_BIT_LSB)
  or  t0, t0, t1
  csrw  menvcfg, t0

  ret

.global jump_to_main
jump_to_main:

  jal start_test_in_machine_mode
  bnez a0, jump_to_main_in_machine_mode

  la  t0, jump_to_main_in_supervisor_mode
  csrw  mepc, t0
  csrr  t0, mstatus
  li  t1, (SUPERVISOR_MODE_ENCODING << MSTATUS_MPP_SHIFT)
  or  t0, t0, t1
  csrw  mstatus, t0

  mret

jump_to_main_in_machine_mode:

  # Add the page containing main to the MCRR_1.
  la t0, main
  # Check that main is at the beginning of a 4K page as we expect this
  # page to be the start of MCRR_1. The test writer can expand MCRR_1 to
  # the adjoining pages following this page.
  li t1, 0xfff
  and t2, t0, t1
  bnez t2, jumpstart_fail

  csrw mcrr_1_base, t0

  li t0, (1 << PAGE_OFFSET)
  not t0, t0
  ori t0, t0, 0x1 # set the valid bit
  csrw mcrr_1_mask, t0

  call main

  j machine_mode_return_point

# syscall handlers

handle_env_call_from_smode:
  # a7 will contain the syscall number

  li t0, SYSCALL_JUMP_TO_MACHINE_MODE_AND_EXIT
  beq a7, t0, machine_mode_return_point

  j jumpstart_fail

# END syscall handlers

# The mtvec.base must always be 4 byte aligned.
.align 2
.global mtvec_trap_handler
mtvec_trap_handler:
  # Save away the function arguments.
  # TODO: save aware more of these as required.
  mv s1, a0

  li  t0, MACHINE_MODE_ENCODING
  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)

  mv a0, s1

  # csrr a0, mcause

  # # returns the address of the trap handler if the test writer
  # # has registered one, else 0.
  # jal get_trap_handler_override

  # beqz a0, 1f

  # jalr x0, a0

# 1:
  li t0, MCAUSE_EC_ENV_CALL_FROM_SMODE
  csrr t1, mcause
  beq t1, t0, handle_env_call_from_smode

  j jumpstart_fail
