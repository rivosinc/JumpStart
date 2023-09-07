# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.machine.end, "ax"

.global _machine_mode_end
_machine_mode_end:
  # a0 will contain diag pass/fail status.

  # Store pass/fail status into the hart status tracker.
  csrr t0, mhartid
  la t1, hart_status_tracker
  add t1, t1, t0
  sb a0, 0(t1)

  # Have all the secondary harts wait on the wfi.
  # the primary hart will go through the exit routine.
  li t1, PRIMARY_HART_ID
  bne t0, t1, just_wfi

  # Check the status of all the active harts.
  # a0: Active hart mask. Gets shifted right as we check each hart.
  # t0: hart_status_tracker address
  # t1: Hart id of the current hart we're checking status of.
  jal get_active_hart_mask_from_machine_mode
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
  bne t4, t6, jumpstart_fail

done_with_current_hart:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_hart_status_loop

  # All harts have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_fail

  li s1, SPIKE_RUN_PASSED

  jal in_qemu_mode
  beqz a0, 1f

  li s1, QEMU_RIVOS_AP_RUN_PASSED

1:
  j run_end_of_sim_sequence

.global jumpstart_fail
jumpstart_fail:
  li s1, SPIKE_RUN_FAILED

  jal in_qemu_mode
  beqz a0, run_end_of_sim_sequence

  li s1, QEMU_RIVOS_AP_RUN_FAILED

run_end_of_sim_sequence:
  # 1. Disable interrupts
  li t0, 0x0
  csrw   mie, t0 # Disable all interrupt types

  bnez a0, run_qemu_end_of_sim_sequence

run_spike_and_rtl_end_of_sim_sequence:
  li     t0, UC_END_OF_SIM_MAGIC_ADDRESS
  csrw   pmarr_base_0, t0
  li     t0, PMARR_0_MAGIC_STORE_MASK_VAL
  csrw   pmarr_mask_0, t0
  fence.i

  # 2. Store PASS/FAIL to magic address
  li t0, END_OF_SIM_MAGIC_ADDRESS
  sw s1, 0(t0)
  fence.i
  cbo.flush  (t0)

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

  # 3. Store PASS/FAIL to the UC magic address
  li t0, UC_END_OF_SIM_MAGIC_ADDRESS
  sw s1, 0(t0)

  # Spike run with --pass-fail will exit with non-zero error
  # code if t0 is not 1
  mv t0, s1
  lui x0, 0xdeadb
  j just_wfi

run_qemu_end_of_sim_sequence:
  # 2. Store PASS/FAIL to Qemu magic address
  li t0, QEMU_RIVOS_AP_END_MAGIC_ADDRESS
  sw s1, 0(t0)

  # 4. In WFI
.global just_wfi
just_wfi:
  wfi

.align PAGE_OFFSET, 0x0
.global jumpstart_machine_mode_end_point
jumpstart_machine_mode_end_point:
