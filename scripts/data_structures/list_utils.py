# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log


class ListUtils:
    def intersection(lst1, lst2):
        log.debug(f"Finding intersection of {lst1} and {lst2}")
        temp = set(lst2)
        lst3 = [value for value in lst1 if value in temp]
        return lst3
