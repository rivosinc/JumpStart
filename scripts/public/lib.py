# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import sys


def sanity_check_memory_map(mappings):
    for mapping in mappings:
        if "no_pte_allocation" in mapping and mapping["no_pte_allocation"] is True:
            pte_attributes = ["xwr", "umode", "va"]
            # if the mapping has a no_pte_allocation attribute, then
            # it should not have any xwr or umode bits set.
            assert not any(x in mapping for x in pte_attributes)

    # check that the memory mappings don't overlap
    # the mappings are sorted by the physical address at this point.
    last_mapping = None
    for mapping in mappings:
        if last_mapping is None:
            last_mapping = mapping
            continue

        last_mapping_size = last_mapping["page_size"] * last_mapping["num_pages"]

        last_mapping_end_address = last_mapping["pa"] + last_mapping_size

        if mapping["pa"] < last_mapping_end_address:
            log.error(f"Memory mapping {mapping} overlaps with {last_mapping}")
            sys.exit(1)

        last_mapping = mapping
