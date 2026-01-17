# SPDX-FileCopyrightText: 2024 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum


class PageSize(enum.IntEnum):
    SIZE_4K = 0x1000
    SIZE_2M = 0x200000
    SIZE_1G = 0x40000000
    SIZE_512G = 0x8000000000
