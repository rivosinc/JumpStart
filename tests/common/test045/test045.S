# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .text.vsmode, "ax"

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
