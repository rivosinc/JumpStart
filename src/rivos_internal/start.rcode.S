# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.rcode.init, "ax"
.global _rcode_start
_rcode_start:
  la t0, _rtvec
  csrw rtvec, t0

  jal update_mcrr_0_to_cover_jumpstart_machine_code

  jal setup_pmarr

  la    t0, _machine_mode_start
  csrw repc, t0
  rret

.org 512
_rtvec:
  wfi

.section .jumpstart.text.rcode, "ax"

update_mcrr_0_to_cover_jumpstart_machine_code:
  # Update the MCRR_0 to include all the machine mode code pages for the
  # jumpstart framework.

  la t0, _JUMPSTART_TEXT_MACHINE_INIT_START
  csrw mcrr_0_base, t0

  la t2, _JUMPSTART_TEXT_MACHINE_INIT_END
  # Check if _JUMPSTART_TEXT_MACHINE_INIT_END is page aligned.
  li t1, ((1 << PAGE_OFFSET) - 1)
  and t3, t2, t1
  beqz t3, 1f

  # It's not page aligned so round it up to the next page.
  srli t2, t2, PAGE_OFFSET
  slli t2, t2, PAGE_OFFSET
  li t1, (1 << PAGE_OFFSET)
  add t2, t2, t1

1:
  addi t1, t2, -1

  # t0 contains _JUMPSTART_TEXT_MACHINE_INIT_START
  # t1 contains the address of the last byte of the last page of the
  # jumpstart mmode text section.
  # The MCRR region will cover a NAPOT number of pages. The build scripts
  # check for this.
  # Find the minimum mask value that will cover the entire text section.

  # Minimum mask value
  li t2, (0xFFFFFFFFFFFFFFFFULL << PAGE_OFFSET)

2:
  and t3, t2, t1
  beq t3, t0, found_suitable_mcrr_0_mask
  slli t2, t2, 1
  j 2b

found_suitable_mcrr_0_mask:
  ori t2, t2, 0x1 # set the valid bit in the mask
  csrw mcrr_0_mask, t2

  ret
