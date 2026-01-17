/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0


#define BYTES_TO_COPY (64 * 8)

.section .text.smode, "ax"

# Inputs:
# a0-a6
.global asm_check_passed_in_arguments
asm_check_passed_in_arguments:
  li t0, 1
  bne a0, t0, asm_check_passed_in_arguments_failed

  li t0, 2
  bne a1, t0, asm_check_passed_in_arguments_failed

  li t0, 3
  bne a2, t0, asm_check_passed_in_arguments_failed

  li t0, 4
  bne a3, t0, asm_check_passed_in_arguments_failed

  li t0, 5
  bne a4, t0, asm_check_passed_in_arguments_failed

  li t0, 6
  bne a5, t0, asm_check_passed_in_arguments_failed

  li t0, 7
  bne a6, t0, asm_check_passed_in_arguments_failed

  li a0, DIAG_PASSED
  j asm_check_passed_in_arguments_return

asm_check_passed_in_arguments_failed:
  li a0, DIAG_FAILED

asm_check_passed_in_arguments_return:
  ret

.global copy_bytes
copy_bytes:
  la t0, source_location
  la t1, destination_location
  addi t2, t0, BYTES_TO_COPY

1:
  ld t3, 0(t0)
  sd t3, 0(t1)
  addi t0, t0, 8
  addi t1, t1, 8
  bne t0, t2, 1b

  li a0, DIAG_PASSED

  ret

.global get_bytes_to_copy
get_bytes_to_copy:
  li a0, BYTES_TO_COPY
  ret

.section .data.smode, "aw"

.global source_location
source_location:
  .rept BYTES_TO_COPY
    .byte 0xab
  .endr

.global destination_location
destination_location:
  .rept BYTES_TO_COPY
    .byte 0xcd
  .endr
