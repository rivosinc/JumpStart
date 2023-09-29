# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import sys


def sanity_check_memory_map(mappings):
    found_text_section = False
    previous_mapping = None
    for mapping in mappings:
        if "no_pte_allocation" in mapping and mapping["no_pte_allocation"] is True:
            pte_attributes = ["xwr", "umode", "va"]
            # if the mapping has a no_pte_allocation attribute, then
            # it should not have any xwr or umode bits set.
            assert not any(x in mapping for x in pte_attributes)

        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping["page_size"] * previous_mapping["num_pages"]

        previous_mapping_end_address = previous_mapping["pa"] + previous_mapping_size

        # the mappings are sorted by the physical address at this point.
        # check that the memory mappings don't overlap
        if mapping["pa"] < previous_mapping_end_address:
            log.error(f"Memory mapping {mapping} overlaps with {previous_mapping}")
            sys.exit(1)

        # The diag should have a .text section.
        if "linker_script_section" in mapping and ".text" in mapping["linker_script_section"].split(
            ","
        ):
            found_text_section = True

        previous_mapping = mapping

    if found_text_section is False:
        log.error("The diag must have a .text section.")
        sys.exit(1)
