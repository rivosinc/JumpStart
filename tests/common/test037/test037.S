/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0


.section .text, "ax"

# Inputs:
#  fa0: A floating point to double.
.global double_float32_number
double_float32_number:
  fadd.s fa0, fa0, fa0

  ret

# Run something.
.global run_vector_instructions
run_vector_instructions:
  vsetivli	zero,8,e32,m1,ta,ma

  vfadd.vf v28, v28, f28
  vfmin.vf v28, v28, f28
  vfdiv.vf v28, v28, f28
  vadd.vx   v28, v20, t4

  ret

.section .data, "aw"

.global data_area
data_area:
  .4byte 0x0
