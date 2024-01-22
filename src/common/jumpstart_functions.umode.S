# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.umode, "ax"

# Inputs:
#   a0: address of the function to run.
#   a1: arg0 to function to run.
.global jump_to_function_in_umode
jump_to_function_in_umode:
  # arg0 needs to be passed to function in a0.
  mv a2, a0
  mv a0, a1

  jalr ra, a2

  # a0 contains the exit code.
  li  a7, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  ecall

  # We shouldn't come back here.
  wfi

.global jumpstart_umode_fail
jumpstart_umode_fail:
  li a0, DIAG_FAILED
  li  a7, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  ecall
