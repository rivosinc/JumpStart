/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.cpu.text.smode.init.enter, "ax"

# In sbi_firmware_boot mode, other firmwares run in M-mode and drop hand over control
# to JumpStart in S-mode. This code is the entry point for such environments.
# We expect that only one cpu is running at this point and all the other
# cpus are in STOPPED state. The running cpu will make SBI HSM calls to
# wake up the other cpus and start them running in S-mode.
# Inputs:
#   a0: This cpu's cpuid.
.global sbi_firmware_trampoline
sbi_firmware_trampoline:
  mv t0, a0
  li t1, 0  # hid = 0
  li t2, ACTIVE_CPU_MASK
  mv t2, a0 # active_cpu_mask

start_active_cpus_loop:
  beq  t1, t0, invoke_sbi_start_cpu_done # Don't run sbi_cpu_start on self.

  andi t3, t2, 1    # t3 = active_cpu_mask & 1
  bnez t3, invoke_sbi_start_cpu # Run sbi_cpu_start on this active cpu.

  j invoke_sbi_start_cpu_done

invoke_sbi_start_cpu:
  mv a0, t1               # param1: cpuid of cpu to start.
  la a1, _smode_start # param2: start_address at which to start the cpu.
  li a2, 0                # param3: opaque
  jal sbi_cpu_start
  bnez a0, jumpstart_smode_fail # Fail if sbi_cpu_start returns non-zero

invoke_sbi_cpu_status:
  mv a0, t1
  jal sbi_cpu_get_status
  bnez a0, jumpstart_smode_fail # Fail if sbi_cpu_get_status returns non-zero

  # the cpu status is returned in a1.
  # SBI CPU status is 0 if the cpu is running. Wait till the cpu is running.
  bnez a1, invoke_sbi_cpu_status

invoke_sbi_start_cpu_done:
  srli t2, t2, 1    # active_cpu_mask >> 1
  beqz t2, start_active_cpus_loop_end # if active_cpu_mask == 0, done.

  addi t1, t1, 1    # hid++
  j start_active_cpus_loop

start_active_cpus_loop_end:
  li  t1, ACTIVE_CPU_MASK
  mv   a0, t0  # $a0 = my_cpu_id
  srl  t1, t1, a0
  andi t1, t1, 1
  bnez t1, _smode_start # go to _smode_start if active thread
                            # or else stop this cpu and wfi
  jal sbi_cpu_stop

  j just_wfi_from_smode # should never get here.

.section .jumpstart.cpu.text.smode, "ax"

# Inputs:
#   a0: cpu id.
.global _smode_start
_smode_start:
  # This code mirrors _mmode_start in start.mmode.S
  mv t0, a0
  li a0, ACTIVE_CPU_MASK
  li t1, 1
  sll t1, t1, t0
  and a0, a0, t1
  # Send all inactive cpus to wfi.
  beqz a0, just_wfi_from_smode

  # Have the cpu mark itself as running.
  la t1, cpu_status_tracker
  add t1, t1, t0
  li t2, CPU_RUNNING
  sb t2, 0(t1)

  mv a0, t0
  jal setup_thread_attributes_from_smode

  # S-mode and M-mode share the same stack.
  GET_THREAD_ATTRIBUTES_CPU_ID(t0)
  li  t1, (NUM_PAGES_PER_CPU_FOR_PRIVILEGED_STACK * PRIVILEGED_STACK_PAGE_SIZE)
  mul t0, t0, t1
  la  t2, privileged_stack_top
  add sp, t2, t0
  add sp, sp, t1 # We want the stack bottom.

  mv  fp, sp

  jal setup_smode

  call main

.global _smode_end
_smode_end:
  # a0 will contain diag pass/fail status.

  # Store pass/fail status into the cpu status tracker.
  GET_THREAD_ATTRIBUTES_CPU_ID(t0)
  la t1, cpu_status_tracker
  add t1, t1, t0
  sb a0, 0(t1)

  # Have all the secondary cpus wait on the wfi.
  # the primary cpu will go through the exit routine.
  li t1, PRIMARY_CPU_ID
  bne t0, t1, just_wfi_from_smode

  CHECKTC_DISABLE

  # Check the status of all the active cpus.
  # a0: Active cpu mask. Gets shifted right as we check each cpu.
  # t0: cpu_status_tracker address
  # t1: CPU id of the current cpu we're checking status of.
  li a0, ACTIVE_CPU_MASK
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
  bne t4, t6, jumpstart_sbi_firmware_boot_fail

done_with_current_cpu:
  srli a0, a0, 1
  addi t1, t1, 1
  bnez a0, check_cpu_status_loop

  CHECKTC_ENABLE

  # All cpus have passed, we're done.
  li t1, DIAG_PASSED
  bne a0, t1, jumpstart_sbi_firmware_boot_fail

  li a0, DIAG_PASSED

  j run_end_of_sim_sequence

.global jumpstart_sbi_firmware_boot_fail
jumpstart_sbi_firmware_boot_fail:
  li a0, DIAG_FAILED

run_end_of_sim_sequence:
  # NOTE: this will not work on RTL simulation.
  slli t1, a0, 1
  ori t1, t1, 1

  la t0, tohost
  sd t1, 0(t0)

  1: j 1b # wait for termination

#define SBI_HSM_EID               0x48534D
#define SBI_HSM_CPU_START_FID    0
#define SBI_HSM_CPU_STOP_FID     1
#define SBI_HSM_CPU_STATUS_FID   2
#define SBI_SRST_EID              0x53525354
#define SBI_SRST_SYSTEM_RESET_FID 0

.section .jumpstart.cpu.text.smode, "ax"

# Reference:
# https://github.com/riscv-non-isa/riscv-sbi-doc/blob/master/src/ext-hsm.adoc

# Prototype:
# struct sbiret sbi_cpu_start(unsigned long cpuid,
#                              unsigned long start_addr,
#                              unsigned long opaque)
.global sbi_cpu_start
sbi_cpu_start:
  li a6, SBI_HSM_CPU_START_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_cpu_stop(void)
.global sbi_cpu_stop
sbi_cpu_stop:
  li a6, SBI_HSM_CPU_STOP_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_cpu_get_status(unsigned long cpuid)
.global sbi_cpu_get_status
sbi_cpu_get_status:
  li a6, SBI_HSM_CPU_STATUS_FID
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


.section .jumpstart.cpu.data.privileged, "aw", @progbits

.align 6
.globl tohost
tohost: .dword 0

.align 6
.globl fromhost
fromhost: .dword 0
