# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_defines.h"

.section .text.jumpstart.init

.global _start
_start:
	la t0, exception_handler
	csrw mtvec, t0

  la  sp, stack
  mv  fp, sp

  jal setup_thread_attributes

  jal main

jumpstart_exit:
  # a0 indicates PASS(1) and FAIL(0)
  # s1 is callee saved
  mv s1, a0

  jal disable_mmu_for_supervisor_mode

  jal jump_to_machine_mode

  li t0, 1
  beqz s1, 1f

.global jumpstart_fail
jumpstart_fail:
  /* if t0 is not 1, spike run with --pass-fail will exit with
  non zero error code */
  li t0, 0

1:
  lui x0, 0xdeadb

  j 1b

  nop
  ret

.section .data

.global thread_attributes_region
thread_attributes_region:
.4byte 0xcafe
.balign 4096

.balign 8
brk:
.long

.balign 4096
heap:
.rep 8192
.byte 0
.endr
stack:
