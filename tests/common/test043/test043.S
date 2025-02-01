/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

.section .jumpstart.cpu.text.mmode.init, "ax"

#padding init area with a whole 4K page to test failure
.global aaa__dummy_array
aaa__dummy_array:
    .space 4096
