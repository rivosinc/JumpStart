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
#   a0: address to load from
.global load_from_address
load_from_address:
  ld a0, 0(a0)
  ret

.section .data.1, "aw"

.global data_area
data_area:
  .8byte 0x0

  .align 12

  .8byte 0x0
