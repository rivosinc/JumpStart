/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0


.section .jumpstart.cpu.text.umode, "ax"

# Inputs:
#   a0: address of the function to run.
#   a1-a7 contains the arguments to pass to the umode function.
.global jump_to_function_in_vumode
jump_to_function_in_vumode:
  mv t0, a0

  # Function arguments have to be passed in a0-a6.
  mv a0, a1
  mv a1, a2
  mv a2, a3
  mv a3, a4
  mv a4, a5
  mv a5, a6
  mv a6, a7

  jalr ra, t0

exit_from_vumode:
  # a0 contains the exit code.
  li  a7, SYSCALL_RUN_FUNC_IN_VUMODE_COMPLETE
  ecall

  # We shouldn't come back here.
  wfi

.global jumpstart_vumode_fail
jumpstart_vumode_fail:
  li a0, DIAG_FAILED
  j exit_from_vumode
