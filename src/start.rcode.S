# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .jumpstart.text.rcode.init, "ax"
.global _rcode_start
_rcode_start:
  la t0, _rtvec
  csrw rtvec, t0

  jal update_mcrr_0_to_cover_jumpstart_machine_code

  jal setup_pmarr

  la    t0, _machine_mode_start
  csrw repc, t0
  rret

.org 512
_rtvec:
  wfi

.section .jumpstart.text.rcode, "ax"

update_mcrr_0_to_cover_jumpstart_machine_code:
  # The reset default of the MCRR_0 is the 4K page starting at the LLC-as-SRAM
  # range base address. We expect _machine_mode_start to be at the beginning of this page.
  # Update the MCRR_0 to include all the machine mode code pages for the
  # jumpstart framework.

  la t0, _machine_mode_start
  csrw mcrr_0_base, t0

  # Determine the size of the jumpstart machine mode code region.
  # We expect it to start at _machine_mode_start (from the .jumpstart.machine.init) section
  # and extend to jumpstart_machine_mode_end_point (from the
  # from the .jumpstart.machine.end
  la t1, jumpstart_machine_mode_end_point
  sub t0, t1, t0

  # Compute the mask for the number of machine mode code pages.
  addi t0, t0, -1
  not t0, t0
  ori t0, t0, 0x1
  csrw mcrr_0_mask, t0

  ret
