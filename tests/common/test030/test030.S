/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart_defines.h"

.section .text
.global asm_test_unaligned_access

# Inputs:
#   a0: pointer to a 16-byte aligned region
#   a1: size of the region
# Returns:
#   a0: DIAG_PASSED or DIAG_FAILED
asm_test_unaligned_access:
  li t6, 1024        # Set stride to 1K
  mv t5, a0         # Current pointer
  add t4, a0, a1    # End pointer

1:
  # perform unaligned loads of all sizes
  lbu t0, 0(t5)
  lhu t1, 1(t5)
  lwu t2, 3(t5)
  ld  t3, 7(t5)

  # perform unaligned stores of all sizes
  sb t0, 0(t5)
  sh t1, 1(t5)
  sw t2, 3(t5)
  sd t3, 7(t5)

  add t5, t5, t6    # Advance pointer by 1K
  bgeu t5, t4, 2f   # Exit if we've reached or exceeded the end
  j 1b              # Continue loop

2:
  li a0, DIAG_PASSED
  ret
