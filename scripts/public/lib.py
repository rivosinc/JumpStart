# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import sys


class PageSize(enum.IntEnum):
    SIZE_4K = 0x1000
    SIZE_2M = 0x200000
    SIZE_1G = 0x40000000
    SIZE_512G = 0x8000000000


def alias_mapping_overlaps_with_existing_mapping(alias_mapping, mappings):
    pa_start = alias_mapping["pa"]
    pa_end = pa_start + (alias_mapping["page_size"] * alias_mapping["num_pages"])

    for mapping in mappings:
        if "alias" in mapping and mapping["alias"] is True:
            continue

        mapping_pa_start = mapping["pa"]
        mapping_pa_end = mapping_pa_start + (mapping["page_size"] * mapping["num_pages"])

        if pa_start >= mapping_pa_start and pa_end <= mapping_pa_end:
            return True

    return False


def sanity_check_memory_map(mappings):
    found_text_section = False
    previous_mapping = None

    # Check for VA overlaps in the mappings.
    mappings_with_va = [mapping for mapping in mappings if "va" in mapping]
    mappings_with_va = sorted(
        mappings_with_va,
        key=lambda x: x["va"],
        reverse=False,
    )
    previous_mapping = None
    for mapping in mappings_with_va:
        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping["page_size"] * previous_mapping["num_pages"]
        previous_mapping_end_va = previous_mapping["va"] + previous_mapping_size

        if mapping["va"] < previous_mapping_end_va:
            log.error("VA overlap in these mappings.")
            log.error(f"\t{mapping}")
            log.error(f"\t{previous_mapping}")
            sys.exit(1)

    # Check that mappings with "no_pte_allocation" entries don't have
    # any of the PTE related attributes.
    pte_attributes = ["xwr", "umode", "va"]
    attributes_not_allowed_for_va_alias = [
        "linker_script_section",
        "pma_memory_type",
        "no_pte_allocation",
    ]
    for mapping in mappings:
        if "no_pte_allocation" in mapping and mapping["no_pte_allocation"] is True:
            assert not any(x in mapping for x in pte_attributes)
        if "alias" in mapping and mapping["alias"] is True:
            if any(x in mapping for x in attributes_not_allowed_for_va_alias):
                log.error(
                    f"Alias mapping has attributes that are not allowed for VA aliases: {attributes_not_allowed_for_va_alias}"
                )
                log.error(f"\t{mapping}")
                sys.exit(1)

            if alias_mapping_overlaps_with_existing_mapping(mapping, mappings) is False:
                log.error(
                    f"PA of Alias mapping does not overlap with an existing mapping: {mapping}"
                )
                sys.exit(1)

    # Check for PA overlaps in the mappings.
    # The mappings should already be sorted by PA.
    previous_mapping = None
    for mapping in mappings:
        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping["page_size"] * previous_mapping["num_pages"]
        previous_mapping_end_pa = previous_mapping["pa"] + previous_mapping_size

        if mapping["pa"] < previous_mapping_end_pa:
            log.error(
                "PA overlap in these mappings. If one of these is an alias add the 'alias: True' attribute for it's entry in the memory map."
            )
            log.error(f"\t{mapping}")
            log.error(f"\t{previous_mapping}")
            sys.exit(1)

        # The diag should have a .text section.
        if "linker_script_section" in mapping and ".text" in mapping["linker_script_section"].split(
            ","
        ):
            found_text_section = True

    if found_text_section is False:
        log.error("The diag must have a .text section.")
        sys.exit(1)
