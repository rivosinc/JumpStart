# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.machine, "ax"

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
