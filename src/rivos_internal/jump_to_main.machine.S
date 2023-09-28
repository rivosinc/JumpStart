# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.machine, "ax"

.global jump_to_main_in_machine_mode
jump_to_main_in_machine_mode:
  # Add the .text section to the MCRR_1.
  la t0, _TEXT_START

  # Check that the start of the text section is page aligned.
  li t1, ((1 << PAGE_OFFSET) - 1)
  and t2, t0, t1
  bnez t2, jumpstart_machine_fail

  la t2, _TEXT_END
  # Check that _TEXT_END is greater than _TEXT_START.
  ble t2, t0, jumpstart_machine_fail

  # Check that main() falls into this region because we're going to jump there.
  la t3, main
  bgt t0, t3, jumpstart_machine_fail
  blt t2, t3, jumpstart_machine_fail

  csrw mcrr_1_base, t0

  # Check if _TEXT_END is page aligned.
  and t3, t2, t1
  beqz t3, 1f

  # It's not page aligned so round it up to the next page.
  srli t2, t2, PAGE_OFFSET
  slli t2, t2, PAGE_OFFSET
  li t1, (1 << PAGE_OFFSET)
  add t2, t2, t1

1:
  addi t1, t2, -1

  # t0 contains _TEXT_START
  # t1 contains the address of the last byte of the last page of the text section.
  # The MCRR region will cover a NAPOT number of pages. The build scripts
  # check for this.
  # Find the minimum mask value that will cover the entire text section.

  # Minimum mask value
  li t2, (0xFFFFFFFFFFFFFFFFULL << PAGE_OFFSET)

2:
  and t3, t2, t1
  beq t3, t0, found_suitable_mcrr_1_mask
  slli t2, t2, 1
  j 2b

found_suitable_mcrr_1_mask:
  ori t2, t2, 0x1 # set the valid bit in the mask
  csrw mcrr_1_mask, t2

  call main

  j _machine_mode_end
