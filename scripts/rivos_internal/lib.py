# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import sys


def get_jumpstart_rcode_text_section_mapping(page_offset,
                                             jumpstart_source_attributes):
    rcode_mapping = {}
    rcode_mapping['pa'] = jumpstart_source_attributes['diag_attributes'][
        'rcode_start_address']
    rcode_mapping['page_size'] = 1 << page_offset
    rcode_mapping['num_pages'] = jumpstart_source_attributes[
        'jumpstart_rcode_text_page_counts']['num_pages_for_all_text']
    rcode_mapping[
        'linker_script_section'] = ".jumpstart.text.rcode.init,.jumpstart.text.rcode"
    # rcode region does not get a PMARR mapping.
    rcode_mapping['no_pte_allocation'] = True

    return rcode_mapping


def get_rivos_specific_mappings(page_offset, jumpstart_source_attributes):
    return get_jumpstart_rcode_text_section_mapping(
        page_offset, jumpstart_source_attributes)
