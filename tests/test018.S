# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

#define BYTES_TO_COPY (64 * 8)

.section .text.supervisor, "ax"

.global copy_bytes
copy_bytes:
  la t0, source_location
  la t1, destination_location
  addi t2, t0, BYTES_TO_COPY

1:
  ld t3, 0(t0)
  sd t3, 0(t1)
  addi t0, t0, 8
  addi t1, t1, 8
  bne t0, t2, 1b

  li a0, DIAG_PASSED

  ret

.global get_bytes_to_copy
get_bytes_to_copy:
  li a0, BYTES_TO_COPY
  ret

.section .data.supervisor, "aw"

.global source_location
source_location:
  .rept BYTES_TO_COPY
    .byte 0xab
  .endr

.global destination_location
destination_location:
  .rept BYTES_TO_COPY
    .byte 0xcd
  .endr
