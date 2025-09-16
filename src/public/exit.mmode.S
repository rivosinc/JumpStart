/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"

.section .jumpstart.cpu.text.mmode.init.exit, "ax"

.global _mmode_end
_mmode_end:
  # a0 will contain diag pass/fail status.

  # Store pass/fail status into the cpu status tracker.
  GET_THREAD_ATTRIBUTES_CPU_ID(t0)
  la t1, cpu_status_tracker
  add t1, t1, t0
  sb a0, 0(t1)

  # The primary cpu will go through the exit routine.
  li t1, PRIMARY_CPU_ID
  beq t0, t1, 1f

  # Secondary cpu.
  # Have all the secondary cpus wait on the wfi.
  j just_wfi_from_mmode

1:
  # Check the status of all the active cpus.
  # a0: Active cpu mask. Gets shifted right as we check each cpu.
  # t0: cpu_status_tracker address
  # t1: CPU id of the current cpu we're checking status of.
  li  a0, ACTIVE_CPU_MASK
  la t0, cpu_status_tracker
  li t1, 0x0

check_cpu_status_loop:
  andi t6, a0, 0x1
  beqz t6, done_with_current_cpu

  # Active core, check it's pass/fail status.
  add t5, t0, t1 # pointer to the cpu's status

  li t6, CPU_INACTIVE
wait_for_inactive_cpu_loop:
  lb t4, 0(t5)
  beq t4, t6, wait_for_inactive_cpu_loop

  li t6, CPU_RUNNING
wait_for_running_cpu_loop:
  lb t4, 0(t5)
  beq t4, t6, wait_for_running_cpu_loop

  li t6, DIAG_PASSED
  bne t4, t6, jumpstart_mmode_fail

done_with_current_cpu:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_cpu_status_loop

  # All cpus have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_mmode_fail

  li a0, DIAG_PASSED

  j run_end_of_sim_sequence

.global jumpstart_mmode_fail
jumpstart_mmode_fail:
  li a0, DIAG_FAILED

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

.section .jumpstart.cpu.data.privileged, "aw", @progbits

.align 6
.globl tohost
tohost: .dword 0

.align 6
.globl fromhost
fromhost: .dword 0
