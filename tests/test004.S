# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.section .text, "ax"

.global hwp_ampm_diag
hwp_ampm_diag:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  nop
  addi x28, x0, 0
  addi x17, x0, 0
  li x29, 32768
  addi x12, x0, 1
  li x5, 256
  addi x6, x0, 0
  addi x13, x0, 0
  la x7, dataregion
  addi x7, x7, 0
  li x16, 64
__PERF_MEASURE_START_G0_RET:
  fence.i
  jal mainloop
  j __PERF_MEASURE_END_G0_RET
mainloop:
  add x30, x7, x17
  lb x14, 0(x30)
  mul x17, x14, x17
  mul x17, x14, x17
  mul x17, x14, x17
  mul x17, x28, x17
  add x30, x30, x17
  add x30, x30, x29
  add x7, x7, x16
  addi x6, x6, 1
  blt x6, x5, mainloop
  la x7, dataregion
  addi x7, x7, 0
  addi x6, x0, 0
  addi x13, x13, 1
  blt x13, x12, mainloop
  ret
  addi x5, x0, 100
__wait_0:
  fence.i
  addi x5, x5, -1
  bgt x5, x0, __wait_0
__PERF_MEASURE_END_G0_RET:
  nop
  xor x0, x0, x0

_diag_end:
  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16

  ret

.section .data, "wa", @progbits
dataregion:
  .balign 32768
