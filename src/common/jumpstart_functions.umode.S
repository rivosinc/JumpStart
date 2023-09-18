# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.umode, "ax"

# a0 contains the address of the function to jump to.
.global jump_to_function_in_umode
jump_to_function_in_umode:

  # A0 contains arg value passed by S mode.
  jalr ra, a0

  # a0 contains the exit code.
  li  a7, SYSCALL_RUN_FUNC_IN_USER_MODE_COMPLETE
  ecall

  # We shouldn't come back here.
  wfi
