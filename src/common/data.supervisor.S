# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#include "jumpstart_defines.h"

# The supervisor data section is can be accessed from both
# machine and supervisor mode.
.section .jumpstart.data.supervisor, "aw"

.global hart_status_tracker
hart_status_tracker:
  .rept MAX_NUM_HARTS_SUPPORTED
    .byte HART_INACTIVE
  .endr


.align 2
.global hart_sync_point
hart_sync_point:
  # We're going to use the amoor.w instruction to update the bits
  # so allocate 4 bytes.
  .4byte 0x0
