/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */


.section .jumpstart.cpu.text.smode, "ax"

.global setup_default_heap
setup_default_heap:
#if ENABLE_HEAP == 1
  addi  sp, sp, -16
  sd    ra, 8(sp)
  sd    fp, 0(sp)
  addi  fp, sp, 16

  la a0, _JUMPSTART_CPU_SMODE_HEAP_START
  # The heap end is set to the last byte of the heap.
  # Add 1 to the heap end to include the last byte.
  la a1, _JUMPSTART_CPU_SMODE_HEAP_END
  addi a1, a1, 1
  li a2, BACKING_MEMORY_DDR
  li a3, MEMORY_TYPE_WB
  jal setup_heap

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
#endif // ENABLE_HEAP == 1

  ret
