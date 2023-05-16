# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.section .text

.global get_hart_id
get_hart_id:
  # TODO: need to implement this but can't read mhartid in S-mode
  li  a0, 0
  ret

#define MSTATUS_SUPERVISOR_SWITCH 0x0000000a00000800

.global jump_to_supervisor_mode
jump_to_supervisor_mode:

  la  t0, 1f
  csrw  mepc, t0
  csrr  t0, mstatus
  li  t1, MSTATUS_SUPERVISOR_SWITCH
  or  t0, t0, t1
  csrw  mstatus, t0
  mret

1:
  ret
