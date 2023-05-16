# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.section .text.init

.global _start
_start:
  nop
  nop
  nop
  nop
  nop
  nop
  nop
  nop

	la t0, 1f
	csrw mtvec, t0

  jal enable_mmu_for_supervisor_mode
  jal jump_to_supervisor_mode

  la  sp, stack
  jal main

  li t0, 1
  beqz a0, 1f

  /* if t0 is not 1, spike run with --pass-fail will exit with
  non zero error code */
  li t0, 0

1:
  lui x0, 0xdeadb

  j 1b

  nop
  ret

.section .data

.balign 8
brk:
.long

.balign 4096
heap:
.rep 8192
.byte 0
.endr
stack:
