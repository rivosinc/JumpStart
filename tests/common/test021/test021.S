# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#define MAGIC_VALUE 0xcafecafecafecafe

.section .text, "ax", @progbits
.global is_load_allowed_to_data_area
is_load_allowed_to_data_area:
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  la t0, data_area

  li t1, 0
  # This access will fault if the PTE has not been marked as valid.
  # The fault handler will just skip over this instruction.
  ld t1, 0(t0)

  li t2, MAGIC_VALUE
  bne t2, t1, access_faulted

  li a0, 1
  j 1f

access_faulted:
  li a0, 0

1:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.section .data.diag, "wa", @progbits
.global data_area
data_area:
  .8byte MAGIC_VALUE
