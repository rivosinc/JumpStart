# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .text, "ax"

# Inputs:
#  fa0: A floating point to double.
.global double_float32_number
double_float32_number:
  fadd.s fa0, fa0, fa0

  ret

.section .data, "aw"

.global data_area
data_area:
  .4byte 0x0
