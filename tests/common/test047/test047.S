# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

.global smode_read_guest_byte_zext
smode_read_guest_byte_zext:
  hlv.bu a0, 0(a0)
  ret

.global smode_read_guest_byte
smode_read_guest_byte:
  hlv.b a0, 0(a0)
  ret

.global smode_read_guest_hword_zext
smode_read_guest_hword_zext:
  hlv.hu a0, 0(a0)
  ret

.global smode_read_guest_hword
smode_read_guest_hword:
  hlv.h a0, 0(a0)
  ret

.global smode_read_guest_word_zext
smode_read_guest_word_zext:
  hlv.wu a0, 0(a0)
  ret

.global smode_read_guest_word
smode_read_guest_word:
  hlv.w a0, 0(a0)
  ret

.global smode_read_guest_dword
smode_read_guest_dword:
  hlv.d a0, 0(a0)
  ret

.global smode_write_guest_byte
smode_write_guest_byte:
  hsv.b a1, 0(a0)
  ret

.global smode_write_guest_hword
smode_write_guest_hword:
  hsv.h a1, 0(a0)
  ret

.global smode_write_guest_word
smode_write_guest_word:
  hsv.w a1, 0(a0)
  ret

.global smode_write_guest_dword
smode_write_guest_dword:
  hsv.d a1, 0(a0)
  ret

.global smode_read_guest_inst_hword
smode_read_guest_inst_byte:
  hlvx.hu a0, 0(a0)
  ret

.global smode_read_guest_inst_word
smode_read_guest_inst_hword:
  hlvx.wu a0, 0(a0)
  ret
