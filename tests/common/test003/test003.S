# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.global test003_illegal_instruction_function
test003_illegal_instruction_function:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  # Make sure that the GPRs are untouched across the illegal instruction trap.
  li t0, 0xf0
  li t1, 0xf1
  li t2, 0xf2
  li t3, 0xf3
  li t4, 0xf4
  li t5, 0xf5
  li t6, 0xf6

  li a0, 0xf0
  li a1, 0xf1
  li a2, 0xf2
  li a3, 0xf3
  li a4, 0xf4
  li a5, 0xf5
  li a6, 0xf6
  li a7, 0xf7

  addi sp, sp, -8

  sd s1, 0(sp)
  sd s2, -8(sp)
  sd s3, -16(sp)
  sd s4, -24(sp)
  sd s5, -32(sp)
  sd s6, -40(sp)
  sd s7, -48(sp)
  sd s8, -56(sp)
  sd s9, -64(sp)
  sd s10, -72(sp)
  sd s11, -80(sp)

  li s1, 0xf1
  li s2, 0xf2
  li s3, 0xf3
  li s4, 0xf4
  li s5, 0xf5
  li s6, 0xf6
  li s7, 0xf7
  li s8, 0xf8
  li s9, 0xf9
  li s10, 0xfa
  li s11, 0xfb

  // Illegal instruction that the custom handler is going to skip over.
  .4byte 0xffffffff

  addi s1, s1, -0xf1
  bnez  s1, test003_illegal_instruction_function_fail
  addi s2, s2, -0xf2
  bnez  s2, test003_illegal_instruction_function_fail
  addi s3, s3, -0xf3
  bnez  s3, test003_illegal_instruction_function_fail
  addi s4, s4, -0xf4
  bnez  s4, test003_illegal_instruction_function_fail
  addi s5, s5, -0xf5
  bnez  s5, test003_illegal_instruction_function_fail
  addi s6, s6, -0xf6
  bnez  s6, test003_illegal_instruction_function_fail
  addi s7, s7, -0xf7
  bnez  s7, test003_illegal_instruction_function_fail
  addi s8, s8, -0xf8
  bnez  s8, test003_illegal_instruction_function_fail
  addi s9, s9, -0xf9
  bnez  s9, test003_illegal_instruction_function_fail
  addi s10, s10, -0xfa
  bnez  s10, test003_illegal_instruction_function_fail
  addi s11, s11, -0xfb
  bnez  s11, test003_illegal_instruction_function_fail

  ld s1, 0(sp)
  ld s2, -8(sp)
  ld s3, -16(sp)
  ld s4, -24(sp)
  ld s5, -32(sp)
  ld s6, -40(sp)
  ld s7, -48(sp)
  ld s8, -56(sp)
  ld s9, -64(sp)
  ld s10, -72(sp)
  ld s11, -80(sp)

  addi sp, sp, 8

  addi t0, t0, -0xf0
  bnez  t0, test003_illegal_instruction_function_fail
  addi t1, t1, -0xf1
  bnez  t1, test003_illegal_instruction_function_fail
  addi t2, t2, -0xf2
  bnez  t2, test003_illegal_instruction_function_fail
  addi t3, t3, -0xf3
  bnez  t3, test003_illegal_instruction_function_fail
  addi t4, t4, -0xf4
  bnez  t4, test003_illegal_instruction_function_fail
  addi t5, t5, -0xf5
  bnez  t5, test003_illegal_instruction_function_fail
  addi t6, t6, -0xf6
  bnez  t6, test003_illegal_instruction_function_fail

  addi a0, a0, -0xf0
  bnez  a0, test003_illegal_instruction_function_fail
  addi a1, a1, -0xf1
  bnez  a1, test003_illegal_instruction_function_fail
  addi a2, a2, -0xf2
  bnez  a2, test003_illegal_instruction_function_fail
  addi a3, a3, -0xf3
  bnez  a3, test003_illegal_instruction_function_fail
  addi a4, a4, -0xf4
  bnez  a4, test003_illegal_instruction_function_fail
  addi a5, a5, -0xf5
  bnez  a5, test003_illegal_instruction_function_fail
  addi a6, a6, -0xf6
  bnez  a6, test003_illegal_instruction_function_fail
  addi a7, a7, -0xf7
  bnez  a7, test003_illegal_instruction_function_fail

  nop
  nop
  nop
  nop

test003_illegal_instruction_function_pass:
  li a0, DIAG_PASSED
  j 1f

test003_illegal_instruction_function_fail:
  li a0, DIAG_FAILED

1:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global alt_test003_illegal_instruction_function
alt_test003_illegal_instruction_function:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  # Make sure that the GPRs are untouched across the illegal instruction trap.
  li t0, 0xb0
  li t1, 0xb1
  li t2, 0xb2
  li t3, 0xb3
  li t4, 0xb4
  li t5, 0xb5
  li t6, 0xb6

  li a0, 0xb0
  li a1, 0xb1
  li a2, 0xb2
  li a3, 0xb3
  li a4, 0xb4
  li a5, 0xb5
  li a6, 0xb6
  li a7, 0xb7

  addi sp, sp, -8

  sd s1, 0(sp)
  sd s2, -8(sp)
  sd s3, -16(sp)
  sd s4, -24(sp)
  sd s5, -32(sp)
  sd s6, -40(sp)
  sd s7, -48(sp)
  sd s8, -56(sp)
  sd s9, -64(sp)
  sd s10, -72(sp)
  sd s11, -80(sp)

  li s1, 0xb1
  li s2, 0xb2
  li s3, 0xb3
  li s4, 0xb4
  li s5, 0xb5
  li s6, 0xb6
  li s7, 0xb7
  li s8, 0xb8
  li s9, 0xb9
  li s10, 0xba
  li s11, 0xbb

  // Illegal instruction that the custom handler is going to skip over.
  .4byte 0xbfffffff

  addi s1, s1, -0xb1
  bnez  s1, test003_illegal_instruction_function_fail
  addi s2, s2, -0xb2
  bnez  s2, test003_illegal_instruction_function_fail
  addi s3, s3, -0xb3
  bnez  s3, test003_illegal_instruction_function_fail
  addi s4, s4, -0xb4
  bnez  s4, test003_illegal_instruction_function_fail
  addi s5, s5, -0xb5
  bnez  s5, test003_illegal_instruction_function_fail
  addi s6, s6, -0xb6
  bnez  s6, test003_illegal_instruction_function_fail
  addi s7, s7, -0xb7
  bnez  s7, test003_illegal_instruction_function_fail
  addi s8, s8, -0xb8
  bnez  s8, test003_illegal_instruction_function_fail
  addi s9, s9, -0xb9
  bnez  s9, test003_illegal_instruction_function_fail
  addi s10, s10, -0xba
  bnez  s10, test003_illegal_instruction_function_fail
  addi s11, s11, -0xbb
  bnez  s11, test003_illegal_instruction_function_fail

  ld s1, 0(sp)
  ld s2, -8(sp)
  ld s3, -16(sp)
  ld s4, -24(sp)
  ld s5, -32(sp)
  ld s6, -40(sp)
  ld s7, -48(sp)
  ld s8, -56(sp)
  ld s9, -64(sp)
  ld s10, -72(sp)
  ld s11, -80(sp)

  addi sp, sp, 8

  addi t0, t0, -0xb0
  bnez  t0, test003_illegal_instruction_function_fail
  addi t1, t1, -0xb1
  bnez  t1, test003_illegal_instruction_function_fail
  addi t2, t2, -0xb2
  bnez  t2, test003_illegal_instruction_function_fail
  addi t3, t3, -0xb3
  bnez  t3, test003_illegal_instruction_function_fail
  addi t4, t4, -0xb4
  bnez  t4, test003_illegal_instruction_function_fail
  addi t5, t5, -0xb5
  bnez  t5, test003_illegal_instruction_function_fail
  addi t6, t6, -0xb6
  bnez  t6, test003_illegal_instruction_function_fail

  addi a0, a0, -0xb0
  bnez  a0, test003_illegal_instruction_function_fail
  addi a1, a1, -0xb1
  bnez  a1, test003_illegal_instruction_function_fail
  addi a2, a2, -0xb2
  bnez  a2, test003_illegal_instruction_function_fail
  addi a3, a3, -0xb3
  bnez  a3, test003_illegal_instruction_function_fail
  addi a4, a4, -0xb4
  bnez  a4, test003_illegal_instruction_function_fail
  addi a5, a5, -0xb5
  bnez  a5, test003_illegal_instruction_function_fail
  addi a6, a6, -0xb6
  bnez  a6, test003_illegal_instruction_function_fail
  addi a7, a7, -0xb7
  bnez  a7, test003_illegal_instruction_function_fail

  j test003_illegal_instruction_function_pass
