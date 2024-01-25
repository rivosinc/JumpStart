# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.mmode, "ax"

.global jump_to_main_in_mmode
jump_to_main_in_mmode:
  call main

  j _mmode_end
