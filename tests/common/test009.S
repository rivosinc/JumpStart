# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .text, "ax"

.global just_nops
just_nops:
  .rept (((1 << PAGE_OFFSET) * 2) / 4)
    nop
  .endr

  ret
