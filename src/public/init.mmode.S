# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.cpu.text.mmode.init, "ax"

.global setup_mmode
setup_mmode:
    ret

.section .jumpstart.cpu.text.mmode.init.end, "ax"

.global _JUMPSTART_CPU_TEXT_MMODE_INIT_BOUNDARY
_JUMPSTART_CPU_TEXT_MMODE_INIT_BOUNDARY:
    j jumpstart_mmode_fail
    ret
