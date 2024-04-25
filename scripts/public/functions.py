# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import sys


def alias_mapping_overlaps_with_existing_mapping(alias_mapping, mappings):
    pa_start = alias_mapping.get_field("pa")
    pa_end = pa_start + (
        alias_mapping.get_field("page_size") * alias_mapping.get_field("num_pages")
    )

    for mapping in mappings:
        if mapping.get_field("alias") is True:
            continue

        mapping_pa_start = mapping.get_field("pa")
        mapping_pa_end = mapping_pa_start + (
            mapping.get_field("page_size") * mapping.get_field("num_pages")
        )

        if pa_start >= mapping_pa_start and pa_end <= mapping_pa_end:
            return True

    return False


def sanity_check_memory_map(mappings):
    found_text_section = False
    previous_mapping = None

    # Check for VA overlaps in the mappings.
    mappings_with_va = [mapping for mapping in mappings if mapping.get_field("va") is not None]
    mappings_with_va = sorted(
        mappings_with_va,
        key=lambda x: x.get_field("va"),
        reverse=False,
    )
    previous_mapping = None
    for mapping in mappings_with_va:
        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping.get_field(
            "page_size"
        ) * previous_mapping.get_field("num_pages")
        previous_mapping_end_va = previous_mapping.get_field("va") + previous_mapping_size

        if mapping.get_field("va") < previous_mapping_end_va:
            log.error("VA overlap in these mappings.")
            log.error(f"\t{mapping}")
            log.error(f"\t{previous_mapping}")
            sys.exit(1)

        previous_mapping = mapping

    for mapping in mappings:
        if mapping.get_field("alias") is True:
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

        previous_mapping_size = previous_mapping.get_field(
            "page_size"
        ) * previous_mapping.get_field("num_pages")
        previous_mapping_end_pa = previous_mapping.get_field("pa") + previous_mapping_size

        if (
            mapping.get_field("pa") < previous_mapping_end_pa
            and mapping.get_field("alias") is False
        ):
            log.error(
                "PA overlap in these mappings. If one of these is an alias add the 'alias: True' attribute for it's entry in the memory map."
            )
            log.error(f"\t{mapping}")
            log.error(f"\t{previous_mapping}")
            sys.exit(1)

        # The diag should have a .text section.
        if mapping.get_field("linker_script_section") is not None and ".text" in mapping.get_field(
            "linker_script_section"
        ).split(","):
            found_text_section = True

        previous_mapping = mapping

    if found_text_section is False:
        log.error("The diag must have a .text section.")
        sys.exit(1)
