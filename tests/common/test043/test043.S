# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

.section .jumpstart.text.mmode.init, "ax"

#padding init area with a whole 4K page to test failure
.global aaa__dummy_array
aaa__dummy_array:
    .space 4096
