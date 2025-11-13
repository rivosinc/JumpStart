/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

.section .text.umode, "ax"
.global test_illegal_instruction_in_umode
test_illegal_instruction_in_umode:
  // Illegal instruction that the custom handler is going to skip over in S-mode
  .4byte 0xffffffff

  li a0, 0
  ret
