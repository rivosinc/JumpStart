# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.section .text.umode, "ax"
.global copy_512_bytes_in_umode
copy_512_bytes_in_umode:
  la t0, source_location
  la t1, destination_location
  addi t2, t0, 64 * 8

loop:
  ld a0, 0(t0)
  sd a0, 0(t1)
  addi t0, t0, 8
  addi t1, t1, 8
  bne t0, t2, loop

  li a0, 0

  ret

.section .data.umode, "aw"
source_location:
  .rept 64
    .8byte 0xcafed92a0546cad6
  .endr

destination_location:
  .rept 64
    .8byte 0x0
  .endr
