# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log


class BitField:
    def extract_bits(value, bit_range):
        msb = bit_range[0]
        lsb = bit_range[1]
        return (value >> lsb) & ((1 << (msb - lsb + 1)) - 1)

    def place_bits(value, bits, bit_range):
        log.debug(f"Placing {bits} in value {hex(value)} at {bit_range}")
        msb = bit_range[0]
        lsb = bit_range[1]
        return (value & ~(((1 << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb)
