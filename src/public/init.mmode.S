# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.text.mmode.init, "ax"

.global setup_mmode
setup_mmode:
    ret

.section .jumpstart.text.mmode.init.end, "ax"

.global _JUMPSTART_TEXT_MMODE_INIT_BOUNDARY
_JUMPSTART_TEXT_MMODE_INIT_BOUNDARY:
    j jumpstart_mmode_fail
    ret
