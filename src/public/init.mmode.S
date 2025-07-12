/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.cpu.text.mmode.init, "ax"

.global setup_mmode
setup_mmode:
    ret

# Input:
#   a0: hartid
# Output:
#   a0: cpuid
.global convert_hart_id_to_cpu_id
convert_hart_id_to_cpu_id:
  mv a0, a0
  ret
