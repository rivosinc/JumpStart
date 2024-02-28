# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.smode.init, "ax"

# In smode_boot mode, other firmwares run in M-mode and drop hand over control
# to JumpStart in S-mode. This code is the entry point for such environments.
# Inputs:
#   a0: hart id.
.global smode_boot_start
smode_boot_start:
  # This code mirrors _mmode_start in start.mmode.S
  mv t0, a0
  jal get_active_hart_mask_from_smode
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

  j smode_boot_end
