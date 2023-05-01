# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#define PAGE_OFFSET 12

#define SATP_MODE_LSB 60

#define MSTATUS_SUPERVISOR_SWITCH 0x0000000a00000800

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

  la  t0, pagetables_start
  srai  t0, t0, PAGE_OFFSET
  li  t1, SATP_MODE
  slli  t1, t1, SATP_MODE_LSB
  add  t0, t0, t1

  csrw  satp, t0
  fence.i

  la  t0, supervisor_mode_entry_point
  csrw  mepc, t0
  csrr  t0, mstatus
  li  t1, MSTATUS_SUPERVISOR_SWITCH
  or  t0, t0, t1
  csrw  mstatus, t0
  mret

supervisor_mode_entry_point:
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

.section .text

.global get_hart_id
get_hart_id:
  # TODO: need to implement this but can't read mhartid in S-mode
  li  a0, 0
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
