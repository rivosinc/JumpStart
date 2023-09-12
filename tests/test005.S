# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

.section .data.dms.wb, "aw"

// 4 4K pages of source data area
.global source_area
source_area:
  .align 12
  .rept 512
    .8byte 0xcafed92a0546cad6
  .endr

  .align 12
  .rept 512
    .8byte 0xcafe614240531226
  .endr

  .align 12
  .rept 512
    .8byte 0xcafeadae53d0dc4e
  .endr

  .align 12
  .rept 512
    .8byte 0xcafe278e086ee9aa
  .endr
.global source_area_end
source_area_end:

.section .data.dms.uc, "aw"

// 4 4K pages of dest area to overrwrite
.global dest_area
dest_area:
  .align 12
  .rept 512
    .8byte 0x5bb2ac42e098e610
  .endr

  .align 12
  .rept 512
    .8byte 0x9639fefd3b35ee19
  .endr

  .align 12
  .rept 512
    .8byte 0x8a17a7143400a6cc
  .endr

  .align 12
  .rept 512
    .8byte 0x21d8e9ee783d772e
  .endr
.global dest_area_end
dest_area_end:
