/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

#define MAGIC_VALUE 0xcafecafecafecafe

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
  .8byte MAGIC_VALUE


.section .data.2, "aw"

.global data_area_2
data_area_2:
  .8byte MAGIC_VALUE + 1


.section .data.3, "aw"

.global data_area_3
data_area_3:
  .8byte MAGIC_VALUE + 2
