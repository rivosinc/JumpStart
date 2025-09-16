/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"

.section .jumpstart.cpu.text.mmode.init, "ax"

.global setup_mmode
setup_mmode:
    ret

# Output:
#   a0: cpuid
.global get_cpu_id
get_cpu_id:
  csrr a0, mhartid
  ret
