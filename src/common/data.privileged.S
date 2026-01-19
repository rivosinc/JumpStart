/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0


# The supervisor data section is can be accessed from both
# machine and supervisor mode.
.section .jumpstart.cpu.data.privileged, "aw"

.global cpu_status_tracker
cpu_status_tracker:
  .rept MAX_NUM_CPUS_SUPPORTED
    .byte CPU_INACTIVE
  .endr


.align 2
.global cpu_sync_point
cpu_sync_point:
  # We're going to use the amoor.w instruction to update the bits
  # so allocate 4 bytes.
  .4byte 0x0
