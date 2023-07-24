# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.rcode.init, "ax"
.global _rcode_start
_rcode_start:
  la t0, _rtvec
  csrw rtvec, t0

  # Update the MCRR_0 registers to point to the Machine Mode code region.
  jal update_mcrr_0

  jal setup_pmarr

  la    t0, _start
  csrw repc, t0
  rret

.org 512
_rtvec:
  wfi

# This section should fall into the initial 4K page set up in MCRR_0
.section .jumpstart.text.machine.init, "ax"

.global _start
_start:
  la t0, mtvec_trap_handler
  csrw mtvec, t0

  # Set up the stack for M-mode and S-mode.
  la  sp, privileged_stack_bottom
  mv  fp, sp

1:
  jal setup_thread_attributes

  jal enable_svpbmt_for_supervisor_mode

  jal enable_trap_delegation_to_supervisor_mode

  j jump_to_main

.section .jumpstart.text.machine, "ax"

.global enable_trap_delegation_to_supervisor_mode
enable_trap_delegation_to_supervisor_mode:
  li t0, (1 << SCAUSE_EC_ENV_CALL_FROM_UMODE) | (1 << SCAUSE_EC_ILLEGAL_INSTRUCTION)
  csrw medeleg, t0

  li t0, (1 << MIDELEG_S_SOFT_INTERRUPT) | (1 << MIDELEG_S_TIMER_INTERRUPT) | (1 << MIDELEG_S_EXT_INTERRUPT)
  csrw mideleg, t0
  ret

.global setup_thread_attributes
setup_thread_attributes:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  csrr a0, mhartid
  li t1, MAX_NUM_CPUS_SUPPORTED
  bgeu a0, t1, jumpstart_fail

  li  t2, THREAD_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t2, a0, t2
  la  t1, thread_attributes_region
  add tp, t1, t2

  csrr a0, mhartid
  jal set_thread_attributes_hart_id_in_machine_mode

  li t0, TRAP_OVERRIDE_ATTRIBUTES_STRUCT_SIZE_IN_BYTES
  mul t0, a0, t0
  la t1, trap_override_attributes_region
  add a0, t1, t0
  la t1, trap_override_attributes_region_end
  # Make sure that we've allocated enough space for this core's trap handler
  # overrides.
  bgeu a0, t1, jumpstart_fail
  jal set_thread_attributes_trap_override_struct_address_in_machine_mode

  li  a0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE
  jal set_thread_attributes_bookend_magic_number_in_machine_mode

  li  a0, MACHINE_MODE_ENCODING
  jal set_thread_attributes_current_mode_in_machine_mode

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
  #define MENVCFG_PBMTE_ENABLE (1 << 62)
  csrr  t0, menvcfg
  li  t1, MENVCFG_PBMTE_ENABLE
  or  t0, t0, t1
  csrw  menvcfg, t0

  ret

.global jump_to_main
jump_to_main:

  jal start_test_in_machine_mode
  beqz a0, jump_to_main_in_supervisor_mode

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

jump_to_main_in_supervisor_mode:

  la  t0, supervisor_jump_to_main
  csrw  mepc, t0
  csrr  t0, mstatus
  li  t1, (SUPERVISOR_MODE_ENCODING << MSTATUS_MPP_SHIFT)
  or  t0, t0, t1
  csrw  mstatus, t0

  mret

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

  li  a0, MACHINE_MODE_ENCODING
  jal set_thread_attributes_current_mode_in_machine_mode

  mv a0, s1

  # csrr a0, mcause

  # # returns the address of the trap handler if the user
  # # has registered one, else 0.
  # jal get_trap_handler_override

  # beqz a0, 1f

  # jalr x0, a0

# 1:
  li t0, MCAUSE_EC_ENV_CALL_FROM_SMODE
  csrr t1, mcause
  beq t1, t0, handle_env_call_from_smode

  j jumpstart_fail
