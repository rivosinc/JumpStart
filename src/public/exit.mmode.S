# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.mmode.init.exit, "ax"

.global _mmode_end
_mmode_end:
  # a0 will contain diag pass/fail status.

  # Store pass/fail status into the hart status tracker.
  csrr t0, mhartid
  la t1, hart_status_tracker
  add t1, t1, t0
  sb a0, 0(t1)

  # The primary hart will go through the exit routine.
  li t1, PRIMARY_HART_ID
  beq t0, t1, 1f

  # Secondary hart.
  # If we're running in batch mode, return the hart.
  li t0, BATCH_MODE
  bnez t0, batch_mode_return_hart

  # otherwise have all the secondary harts wait on the wfi.
  j just_wfi_from_mmode

1:
  # Check the status of all the active harts.
  # a0: Active hart mask. Gets shifted right as we check each hart.
  # t0: hart_status_tracker address
  # t1: Hart id of the current hart we're checking status of.
  li  a0, ACTIVE_HART_MASK
  la t0, hart_status_tracker
  li t1, 0x0

check_hart_status_loop:
  andi t6, a0, 0x1
  beqz t6, done_with_current_hart

  # Active core, check it's pass/fail status.
  add t5, t0, t1 # pointer to the hart's status

  li t6, HART_INACTIVE
wait_for_inactive_hart_loop:
  lb t4, 0(t5)
  beq t4, t6, wait_for_inactive_hart_loop

  li t6, HART_RUNNING
wait_for_running_hart_loop:
  lb t4, 0(t5)
  beq t4, t6, wait_for_running_hart_loop

  li t6, DIAG_PASSED
  bne t4, t6, jumpstart_mmode_fail

done_with_current_hart:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_hart_status_loop

  # All harts have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_mmode_fail

  li a0, DIAG_PASSED

  j run_end_of_sim_sequence

.global jumpstart_mmode_fail
jumpstart_mmode_fail:
  li a0, DIAG_FAILED

  li t0, BATCH_MODE
  bnez t0, batch_mode_return_hart

run_end_of_sim_sequence:
  slli a0, a0, 1
  ori a0, a0, 1

  la t0, tohost
  sd a0, 0(t0)

  1: j 1b # wait for termination

.global just_wfi_from_mmode
just_wfi_from_mmode:
  wfi
  j just_wfi_from_mmode

.global batch_mode_return_unused_hart
batch_mode_return_unused_hart:
  li a0, DIAG_PASSED
# a0: return value
.global batch_mode_return_hart
batch_mode_return_hart:
  la t0, batch_mode_exit_lock
acquire_exit_lock:
  ld t1, (t0)
  bnez t1, acquire_exit_lock
  li t2, 1
  amoswap.d.aq t2, t2, (t0)
  bnez t2, acquire_exit_lock

  la t1, batch_mode_exit_address
  ld ra, (t1)

release_exit_lock:
  sd zero, (t0)
  csrw mepc, ra
  li t0, MSTATUS_MPP
  csrw mstatus, t0
  mret

.section .jumpstart.data.smode, "aw", @progbits

.align 8
.global batch_mode_exit_address
batch_mode_exit_address:
  .8byte 0
.global batch_mode_exit_lock
batch_mode_exit_lock:
  # initial state is locked. This is set to zero by primary hart after saving return address
  .8byte 1

.align 6
.globl tohost
tohost: .dword 0

.align 6
.globl fromhost
fromhost: .dword 0
