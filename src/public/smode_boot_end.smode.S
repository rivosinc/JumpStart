# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.smode, "ax"

.global smode_boot_end
smode_boot_end:
  # a0 will contain diag pass/fail status.

  # Store pass/fail status into the hart status tracker.
  GET_THREAD_ATTRIBUTES_HART_ID(t0)
  la t1, hart_status_tracker
  add t1, t1, t0
  sb a0, 0(t1)

  # Have all the secondary harts wait on the wfi.
  # the primary hart will go through the exit routine.
  li t1, PRIMARY_HART_ID
  bne t0, t1, just_wfi_from_smode

  # Check the status of all the active harts.
  # a0: Active hart mask. Gets shifted right as we check each hart.
  # t0: hart_status_tracker address
  # t1: Hart id of the current hart we're checking status of.
  jal get_active_hart_mask_from_smode
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
  bne t4, t6, jumpstart_smode_boot_fail

done_with_current_hart:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_hart_status_loop

  # All harts have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_smode_boot_fail

  li a0, DIAG_PASSED

  j run_end_of_sim_sequence

.global jumpstart_smode_boot_fail
jumpstart_smode_boot_fail:
  li a0, DIAG_FAILED

run_end_of_sim_sequence:
  # NOTE: this will not work on RTL simulation.
  slli t1, a0, 1
  ori t1, t1, 1

  la t0, tohost
  sd t1, 0(t0)

  1: j 1b # wait for termination

.section .jumpstart.data.smode, "aw", @progbits

.align 6
.globl tohost
tohost: .dword 0

.align 6
.globl fromhost
fromhost: .dword 0
