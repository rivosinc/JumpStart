/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0


.section .jumpstart.cpu.text.mmode, "ax"

.global jump_to_main_in_mmode
jump_to_main_in_mmode:
  call main

  j _mmode_end
