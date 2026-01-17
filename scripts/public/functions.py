# SPDX-FileCopyrightText: 2023 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

from memory_management import TranslationStage


def check_for_address_overlaps(address_type, mappings):
    mappings = sorted(
        mappings,
        key=lambda x: x.get_field(address_type),
        reverse=False,
    )

    previous_mapping = None
    for mapping in mappings:
        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping.get_field(
            "page_size"
        ) * previous_mapping.get_field("num_pages")
        previous_mapping_end_va = previous_mapping.get_field(address_type) + previous_mapping_size

        if mapping.get_field(address_type) < previous_mapping_end_va:
            raise ValueError(
                f"{address_type.upper()} overlap in these mappings.\n\t{mapping}\n\t{previous_mapping}"
            )

        previous_mapping = mapping


def sanity_check_memory_map(mappings):
    # TODO: Do we expect there to be a translation for the .text section
    # in all translattion stages? Right now we only check that there is one
    # in each stage.
    found_text_section = False

    for stage in TranslationStage.get_enabled_stages():
        mappings_with_source_addresses = []
        alias_mappings = []
        non_alias_mappings = []

        for mapping in mappings[stage]:
            if stage != mapping.get_field("translation_stage"):
                raise ValueError(
                    f"Translation stage mismatch in mapping: {mapping}. Expected: {stage}"
                )

            if mapping.get_field(TranslationStage.get_translates_from(stage)) is not None:
                mappings_with_source_addresses.append(mapping)
                if mapping.get_field("alias") is True:
                    # Only mappings with sources addresses can be aliases.
                    alias_mappings.append(mapping)

            if mapping.get_field("alias") is False:
                non_alias_mappings.append(mapping)

        # Look for overlaps in the source addresses (VA, GPA).
        check_for_address_overlaps(
            TranslationStage.get_translates_from(stage), mappings_with_source_addresses
        )

        # Look for overlaps in the destination addresses (GPA, PA)
        # in mappings that are not aliases.
        check_for_address_overlaps(TranslationStage.get_translates_to(stage), non_alias_mappings)

        # Make sure that the destination address of each alias mapping overlaps
        # with the destination address of a non-alias mapping.
        for alias_mapping in alias_mappings:
            found_overlap = False

            alias_mapping_addr_start = alias_mapping.get_field(
                TranslationStage.get_translates_to(stage)
            )
            alias_mapping_addr_end = alias_mapping_addr_start + (
                alias_mapping.get_field("page_size") * alias_mapping.get_field("num_pages")
            )

            for non_alias_mapping in non_alias_mappings:
                non_alias_mapping_addr_start = non_alias_mapping.get_field(
                    TranslationStage.get_translates_to(stage)
                )
                non_alias_mapping_addr_end = non_alias_mapping_addr_start + (
                    non_alias_mapping.get_field("page_size")
                    * non_alias_mapping.get_field("num_pages")
                )

                if (
                    alias_mapping_addr_start >= non_alias_mapping_addr_start
                    and alias_mapping_addr_end <= non_alias_mapping_addr_end
                ):
                    found_overlap = True

            if found_overlap is False:
                raise ValueError(
                    f"Destination address of Alias mapping does not overlap with an existing mapping: {alias_mapping}"
                )

        for mapping in non_alias_mappings:
            if mapping.get_field(
                "linker_script_section"
            ) is not None and ".text" in mapping.get_field("linker_script_section").split(","):
                found_text_section = True

    if found_text_section is False:
        raise ValueError("The diag must have a .text section.")
