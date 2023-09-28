# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

.section .jumpstart.text.machine, "ax"

.global jump_to_main_in_machine_mode
jump_to_main_in_machine_mode:
  # Add the page containing main to the MCRR_1.
  la t0, main
  # Check that main is at the beginning of a 4K page as we expect this
  # page to be the start of MCRR_1. The test writer can expand MCRR_1 to
  # the adjoining pages following this page.
  li t1, 0xfff
  and t2, t0, t1
  bnez t2, jumpstart_machine_fail

  csrw mcrr_1_base, t0

  li t0, (1 << PAGE_OFFSET)
  not t0, t0
  ori t0, t0, 0x1 # set the valid bit
  csrw mcrr_1_mask, t0

  call main

  j _machine_mode_end
