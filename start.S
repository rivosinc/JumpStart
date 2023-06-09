# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .text.jumpstart.machine.init

.global _start
_start:
  la t0, mtvec_trap_handler
  csrw mtvec, t0

  la  sp, stack
  mv  fp, sp

  jal is_Xrivospagewalk_supported
  beqz a0, 1f
  jal setup_mcrr
  jal setup_pmarr

1:
  jal setup_thread_attributes

  jal enable_svpbmt_for_supervisor_mode

  jal enable_trap_delegation_to_supervisor_mode

  j jump_to_supervisor_mode_and_main

# This function should fall into the initial 4K page set up in MCRR_0
.global setup_mcrr
setup_mcrr:
  # The reset default of the MCRR_0 is to be the LLC-as-SRAM
  # range base address (0x7F800000) and the mask of MCRR_0 to be
  # 4 KiB and marked valid.
  # Update the mask based on the number of machine mode code pages that this
  # diag actually has.

  # Determine the size of the machine mode code region.
  # The supervisor_entry_point immediately follows the machine mode code.
  la t0, _start
  la t1, supervisor_entry_point
  sub t0, t1, t0
  # The machine mode region size should always be a multiple of 4K.
  li t1, 0xfff
  and t2, t0, t1
  bnez t2, jumpstart_fail

  # Compute the mask for the number of machine mode code pages.
  addi t0, t0, -1
  not t0, t0
  # Set the valid bit.
  ori t0, t0, 0x1
  csrw mcrr_0_mask, t0

  ret

.global is_Xrivospagewalk_supported
is_Xrivospagewalk_supported:
  # HACK: detect whether we're running with the Xrivospagewalk extension
  # enabled by checking our _start address. Tests that boot at 0x80000000
  # don't have the extension enabled.
  la t0, _start
  li t1, SOC_TB_BOOT_ADDRESS

  li a0, 1
  bne t0, t1, 1f
  li a0, 0

1:
  ret

.section .text.jumpstart.machine

.global enable_trap_delegation_to_supervisor_mode
enable_trap_delegation_to_supervisor_mode:
  li t0, (1 << SCAUSE_EC_ENV_CALL_FROM_UMODE) | (1 << SCAUSE_EC_ILLEGAL_INSTRUCTION)
  csrw medeleg, t0

  ret

.global machine_mode_return_point
machine_mode_return_point:

  # On the return from supervisor mode, a0 will contain 0 for PASS
  # and non-zero for FAIL.
  # This is the inverse of the Spike/RTL exit condition so flip this.
  bnez a0, jumpstart_fail

  li s1, 1
  j 1f

.global jumpstart_fail
jumpstart_fail:
  # exit code of 0 indicates FAIL.
  li s1, 0

1:
  # We expect to be in machine mode at this point.

  # Three end of sim steps:
  # 1. Disable interrupts
  li t0, 0x0
  csrw   mie, t0 # Disable all interrupt types

  # 2. Store PASS/FAIL to magic address
  li t0, END_OF_SIM_MAGIC_ADDRESS
  sw s1, 0(t0)

  # Need to push the line out of the cache so
  # that the memory transactor can pick up a fail.
  # Change this if/when we have a cache flush op.
  li     x1, L2CACHE_WAY_SIZE
  li     t2, L2CACHE_NUM_WAYS

loop_magic_store:
  # Store the exit signature over and over (see above comment).
  add    t0, t0, x1
  sw     s1, 0(t0)
  addi   t2, t2, -1
  bne    t2, x0, loop_magic_store

  # Spike run with --pass-fail will exit with non-zero error
  # code if t0 is not 1
  mv t0, s1
  lui x0, 0xdeadb

  # 3. In WFI
  wfi


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
  la t1, trap_handler_overrides
  add a0, t1, t0
  la t1, trap_handler_overrides_end
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

.global jump_to_supervisor_mode_and_main
jump_to_supervisor_mode_and_main:
  la  t0, supervisor_entry_point
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


.section .data.jumpstart

.global thread_attributes_region
thread_attributes_region:
.4byte 0x0
.balign 4096

.global trap_handler_overrides
trap_handler_overrides:
.4byte 0x0
.balign 4096

.global trap_handler_overrides_end
trap_handler_overrides_end:

.balign 8
brk:
.long

.balign 4096
heap:
.rep 8192
.byte 0
.endr
stack:
