# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.global main
main:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi  fp, sp, 16

  jal test016_main

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global test016_illegal_instruction_function
test016_illegal_instruction_function:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  // Illegal instruction that the custom handler is going to skip over.
  .4byte 0xffffffff

  nop
  nop
  nop
  nop

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.align 2
.global test016_illegal_instruction_handler
test016_illegal_instruction_handler:
  # skip over the illegal instruction
  csrr a0, mepc
  addi a0, a0, 4
  csrw mepc, a0

  ret
