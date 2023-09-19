# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.machine, "ax"

.global jump_to_main_in_machine_mode
jump_to_main_in_machine_mode:
  call main

  j _machine_mode_end
