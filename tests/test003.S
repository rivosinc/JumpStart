# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.global test003_illegal_instruction_function
test003_illegal_instruction_function:
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
.global test003_illegal_instruction_handler
test003_illegal_instruction_handler:
  # skip over the illegal instruction
  csrr ra, sepc
  addi ra, ra, 4

  ret
