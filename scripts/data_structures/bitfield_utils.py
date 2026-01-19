# SPDX-FileCopyrightText: 2024 - 2026 Rivos Inc.
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

    @staticmethod
    def find_lowest_set_bit(value):
        """
        Find the position of the lowest set bit (0-indexed).

        Args:
            value (int): The integer value to search

        Returns:
            int: The position of the lowest set bit (0-indexed), or -1 if no bits are set

        Examples:
            find_lowest_set_bit(0b1010) -> 1  # bit 1 is the lowest set bit
            find_lowest_set_bit(0b1000) -> 3  # bit 3 is the lowest set bit
            find_lowest_set_bit(0b0000) -> -1 # no bits are set
        """
        if value == 0:
            return -1
        return (value & -value).bit_length() - 1

    @staticmethod
    def find_highest_set_bit(value):
        """
        Find the position of the highest set bit (0-indexed).

        Args:
            value (int): The integer value to search

        Returns:
            int: The position of the highest set bit (0-indexed), or -1 if no bits are set

        Examples:
            find_highest_set_bit(0b1010) -> 3  # bit 3 is the highest set bit
            find_highest_set_bit(0b1000) -> 3  # bit 3 is the highest set bit
            find_highest_set_bit(0b0001) -> 0  # bit 0 is the highest set bit
            find_highest_set_bit(0b0000) -> -1 # no bits are set
        """
        if value == 0:
            return -1
        return value.bit_length() - 1
