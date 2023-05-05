# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

.section .text

.global get_hart_id
get_hart_id:
  # TODO: need to implement this but can't read mhartid in S-mode
  li  a0, 0
  ret
