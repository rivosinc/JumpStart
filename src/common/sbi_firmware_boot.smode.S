# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.cpu.text.smode.init.enter, "ax"

# In sbi_firmware_boot mode, other firmwares run in M-mode and drop hand over control
# to JumpStart in S-mode. This code is the entry point for such environments.
# We expect that only one hart is running at this point and all the other
# harts are in STOPPED state. The running hart will make SBI HSM calls to
# wake up the other harts and start them running in S-mode.
# Inputs:
#   a0: This hart's hartid.
.global sbi_firmware_trampoline
sbi_firmware_trampoline:
  mv t0, a0
  li t1, 0  # hid = 0
  li t2, ACTIVE_HART_MASK
  mv t2, a0 # active_hart_mask

start_active_harts_loop:
  beq  t1, t0, invoke_sbi_start_hart_done # Don't run sbi_hart_start on self.

  andi t3, t2, 1    # t3 = active_hart_mask & 1
  bnez t3, invoke_sbi_start_hart # Run sbi_hart_start on this active hart.

  j invoke_sbi_start_hart_done

invoke_sbi_start_hart:
  mv a0, t1               # param1: hartid of hart to start.
  la a1, _smode_start # param2: start_address at which to start the hart.
  li a2, 0                # param3: opaque
  jal sbi_hart_start
  bnez a0, jumpstart_smode_fail # Fail if sbi_hart_start returns non-zero

invoke_sbi_hart_status:
  mv a0, t1
  jal sbi_hart_get_status
  bnez a0, jumpstart_smode_fail # Fail if sbi_hart_get_status returns non-zero

  # the hart status is returned in a1.
  # SBI HART status is 0 if the hart is running. Wait till the hart is running.
  bnez a1, invoke_sbi_hart_status

invoke_sbi_start_hart_done:
  srli t2, t2, 1    # active_hart_mask >> 1
  beqz t2, start_active_harts_loop_end # if active_hart_mask == 0, done.

  addi t1, t1, 1    # hid++
  j start_active_harts_loop

start_active_harts_loop_end:
  li  t1, ACTIVE_HART_MASK
  mv   a0, t0  # $a0 = my_hart_id
  srl  t1, t1, a0
  andi t1, t1, 1
  bnez t1, _smode_start # go to _smode_start if active thread
                            # or else stop this hart and wfi
  jal sbi_hart_stop

  j just_wfi_from_smode # should never get here.

.section .jumpstart.cpu.text.smode, "ax"

# Inputs:
#   a0: hart id.
.global _smode_start
_smode_start:
  # This code mirrors _mmode_start in start.mmode.S
  mv t0, a0
  li a0, ACTIVE_HART_MASK
  li t1, 1
  sll t1, t1, t0
  and a0, a0, t1
  # Send all inactive harts to wfi.
  beqz a0, just_wfi_from_smode

  # Have the hart mark itself as running.
  la t1, hart_status_tracker
  add t1, t1, t0
  li t2, HART_RUNNING
  sb t2, 0(t1)

  mv a0, t0
  jal setup_thread_attributes_from_smode

  # S-mode and M-mode share the same stack.
  GET_THREAD_ATTRIBUTES_HART_ID(t0)
  li  t1, (NUM_PAGES_PER_HART_FOR_SMODE_STACK * SMODE_STACK_PAGE_SIZE)
  mul t0, t0, t1
  la  t2, smode_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  mv  fp, sp

  jal setup_smode

  call main

.global _smode_end
_smode_end:
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

  CHECKTC_DISABLE

  # Check the status of all the active harts.
  # a0: Active hart mask. Gets shifted right as we check each hart.
  # t0: hart_status_tracker address
  # t1: Hart id of the current hart we're checking status of.
  li a0, ACTIVE_HART_MASK
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
  bne t4, t6, jumpstart_sbi_firmware_boot_fail

done_with_current_hart:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_hart_status_loop

  CHECKTC_ENABLE

  # All harts have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_sbi_firmware_boot_fail

  li a0, DIAG_PASSED

  j run_end_of_sim_sequence

.global jumpstart_sbi_firmware_boot_fail
jumpstart_sbi_firmware_boot_fail:
  li a0, DIAG_FAILED

run_end_of_sim_sequence:
  # NOTE: this will not work on RTL simulation.
  li t1, IN_QEMU_MODE
  bnez t1, invoke_sbi_reset
  slli t1, a0, 1
  ori t1, t1, 1

  la t0, tohost
  sd t1, 0(t0)

  1: j 1b # wait for termination

invoke_sbi_reset:
  mv a1, a0
  li a0, 0 # sbi_system_reset: param1(a0): SHUTDOWN
           # sbi_system_reset: param2(a1): DIAG_PASS(0)/DIAG_FAIL(1)
  jal sbi_system_reset
  j just_wfi_from_smode

#define SBI_HSM_EID               0x48534D
#define SBI_HSM_HART_START_FID    0
#define SBI_HSM_HART_STOP_FID     1
#define SBI_HSM_HART_STATUS_FID   2
#define SBI_SRST_EID              0x53525354
#define SBI_SRST_SYSTEM_RESET_FID 0

.section .jumpstart.cpu.text.smode, "ax"

# Reference:
# https://github.com/riscv-non-isa/riscv-sbi-doc/blob/master/src/ext-hsm.adoc

# Prototype:
# struct sbiret sbi_hart_start(unsigned long hartid,
#                              unsigned long start_addr,
#                              unsigned long opaque)
.global sbi_hart_start
sbi_hart_start:
  li a6, SBI_HSM_HART_START_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_hart_stop(void)
.global sbi_hart_stop
sbi_hart_stop:
  li a6, SBI_HSM_HART_STOP_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_hart_get_status(unsigned long hartid)
.global sbi_hart_get_status
sbi_hart_get_status:
  li a6, SBI_HSM_HART_STATUS_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_system_reset(uint32_t reset_type, uint32_t reset_reason)
.global sbi_system_reset
sbi_system_reset:
  li a6, SBI_SRST_SYSTEM_RESET_FID
  li a7, SBI_SRST_EID
  ecall
  ret


.section .jumpstart.cpu.data.smode, "aw", @progbits

.align 6
.globl tohost
tohost: .dword 0

.align 6
.globl fromhost
fromhost: .dword 0
