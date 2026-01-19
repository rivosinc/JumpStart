# SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

from typing import Tuple


def is_napot_size(size: int) -> bool:
    """
    Check if a size is a NAPOT (Naturally Aligned Power Of Two) value.

    Args:
        size: The size to check

    Returns:
        True if the size is a NAPOT value, False otherwise
    """
    return size > 0 and (size & (size - 1)) == 0


def get_next_napot_size(size: int) -> int:
    """
    Get the next larger NAPOT size that can cover the given size.

    Args:
        size: The minimum size needed

    Returns:
        The next larger NAPOT size that can cover the given size
    """
    if size <= 0:
        return 1

    if is_napot_size(size):
        return size

    # Find the next larger NAPOT value
    napot_size = 1
    while napot_size < size:
        napot_size <<= 1

    return napot_size


def get_previous_napot_size(size: int) -> int:
    """
    Get the previous smaller NAPOT size.

    Args:
        size: The size to find the previous NAPOT for

    Returns:
        The previous smaller NAPOT size
    """
    if size <= 1:
        return 1

    # Find the next larger NAPOT value first
    next_napot = get_next_napot_size(size)

    # If the input size is already NAPOT, return it
    if next_napot == size:
        return size

    # Otherwise, return the previous NAPOT
    return next_napot >> 1


def get_napot_sizes_for_range(size: int) -> Tuple[int, int]:
    """
    Get both the previous and next NAPOT sizes for a given size.

    Args:
        size: The size to find NAPOT sizes for

    Returns:
        A tuple of (previous_napot_size, next_napot_size)
    """
    next_napot = get_next_napot_size(size)
    prev_napot = get_previous_napot_size(size)

    return (prev_napot, next_napot)


def align_to_napot_size(address: int, napot_size: int) -> int:
    """
    Align an address to a NAPOT size boundary.

    Args:
        address: The address to align
        napot_size: The NAPOT size to align to

    Returns:
        The aligned address

    Raises:
        ValueError: If napot_size is not a valid NAPOT value
    """

    # Validate that napot_size is actually a NAPOT value
    if not is_napot_size(napot_size):
        raise ValueError(f"napot_size {napot_size} is not a valid NAPOT value")

    # If already aligned, return as-is
    if address & (napot_size - 1) == 0:
        return address

    # Find the next aligned address
    return (address + napot_size - 1) & ~(napot_size - 1)
