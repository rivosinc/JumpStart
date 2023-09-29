# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import sys


class PmarrRegionMemoryType(enum.IntEnum):
    PMA_UC = 0
    PMA_WC = 1
    PMA_WB = 3


class PmarrAttributes:
    base_lsb = 20
    mask_lsb = 20

    # Minimum size os 1M
    minimum_size = 1024 * 1024

    # The number of PMARR register pairs
    num_registers = 10

    def __init__(self) -> None:
        pass

    def convert_memory_type_to_string(self, memory_type):
        if memory_type == PmarrRegionMemoryType.PMA_UC:
            return "uc"
        elif memory_type == PmarrRegionMemoryType.PMA_WC:
            return "wc"
        elif memory_type == PmarrRegionMemoryType.PMA_WB:
            return "wb"
        else:
            log.error(f"Unknown memory type {memory_type}")
            sys.exit(1)

    def convert_string_to_memory_type(self, memory_type_string):
        if memory_type_string == "uc":
            return PmarrRegionMemoryType.PMA_UC
        elif memory_type_string == "wc":
            return PmarrRegionMemoryType.PMA_WC
        elif memory_type_string == "wb":
            return PmarrRegionMemoryType.PMA_WB
        else:
            log.error(f"Unknown memory type {memory_type_string}")
            sys.exit(1)


class PmarrRegion:
    pmarr_attributes = PmarrAttributes()

    def __init__(self, start_address, end_address, memory_type_string) -> None:
        self.start_address = (
            start_address >> self.pmarr_attributes.base_lsb
        ) << self.pmarr_attributes.base_lsb

        self.end_address = self.start_address + self.pmarr_attributes.minimum_size
        if end_address > self.end_address:
            self.end_address = end_address

        self.memory_type = self.pmarr_attributes.convert_string_to_memory_type(memory_type_string)

    def __str__(self):
        return f"PmarrRegion: start_address={hex(self.start_address)}, end_address={hex(self.end_address)}, memory_type={self.pmarr_attributes.convert_memory_type_to_string(self.memory_type)}"

    def can_add_to_region(self, start_address, end_address, memory_type_string):
        memory_type = self.pmarr_attributes.convert_string_to_memory_type(memory_type_string)

        if (
            (self.start_address <= (end_address - 1))
            and (start_address <= (self.end_address - 1))
            and memory_type != self.memory_type
        ):
            log.error(
                f"Region [{hex(start_address)}, {hex(end_address)}, {memory_type_string}] overlaps with an existing PMARR region [{hex(self.start_address)}, {hex(self.end_address)}] with different memory type {self.pmarr_attributes.convert_memory_type_to_string(self.memory_type)}"
            )
            sys.exit(1)

        if (
            (self.start_address <= end_address)
            and (start_address <= self.end_address)
            and memory_type == self.memory_type
        ):
            return True

        return False

    def add_to_region(self, start_address, end_address):
        assert (self.start_address <= end_address) and (start_address <= self.end_address)

        if start_address < self.start_address:
            self.start_address = start_address

        if self.end_address < end_address:
            self.end_address = end_address

    def generate_pmarr_region_setup_code(self, file_descriptor, reg_id):
        file_descriptor.write(f"   # {reg_id}: {self}\n")

        pmarr_base_reg_value = int(self.memory_type) | self.start_address

        region_size = self.end_address - self.start_address
        # Assuming that the region size is a multiple of the minimum size
        assert region_size % self.pmarr_attributes.minimum_size == 0
        pmarr_mask = (0xFFFFFFFFFFFFFFFF << (region_size.bit_length() - 1)) & 0xFFFFFFFFFFFFFFFF
        pmarr_mask_reg_value = pmarr_mask | 0x3  # set the L and V bits.

        file_descriptor.write(f"   li   t0, {hex(pmarr_base_reg_value)}\n")
        file_descriptor.write(f"   csrw pmarr_base_{reg_id}, t0\n")
        file_descriptor.write(f"   li   t0, {hex(pmarr_mask_reg_value)}\n")
        file_descriptor.write(f"   csrw pmarr_mask_{reg_id}, t0\n\n")


def get_jumpstart_rcode_text_section_mapping(page_offset, jumpstart_source_attributes):
    rcode_mapping = {}
    rcode_mapping["pa"] = jumpstart_source_attributes["diag_attributes"]["rcode_start_address"]
    rcode_mapping["page_size"] = 1 << page_offset
    rcode_mapping["num_pages"] = jumpstart_source_attributes["jumpstart_rcode_text_page_counts"][
        "num_pages_for_all_text"
    ]
    rcode_mapping["linker_script_section"] = ".jumpstart.text.rcode.init,.jumpstart.text.rcode"
    # rcode region does not get a PMARR mapping.
    rcode_mapping["no_pte_allocation"] = True

    return rcode_mapping


def get_rivos_specific_mappings(page_offset, jumpstart_source_attributes):
    return get_jumpstart_rcode_text_section_mapping(page_offset, jumpstart_source_attributes)


def get_rivos_specific_previous_mapping_size(previous_mapping, current_mapping_pmarr_memory_type):
    previous_mapping_size = previous_mapping["page_size"] * previous_mapping["num_pages"]

    previous_mapping_pmarr_memory_type = (
        previous_mapping["pma_memory_type"] if "pma_memory_type" in previous_mapping else None
    )

    if (
        previous_mapping_pmarr_memory_type is not None
        and previous_mapping_pmarr_memory_type != current_mapping_pmarr_memory_type
        and previous_mapping_size < PmarrAttributes.minimum_size
    ):
        log.debug(
            f"Placing new mapping {previous_mapping_size} bytes after {previous_mapping} to account for PMARR minimum size of {PmarrAttributes.minimum_size}"
        )
        previous_mapping_size = PmarrAttributes.minimum_size

    return previous_mapping_size


def sanity_check_memory_map(diag_attributes):
    mappings = diag_attributes["mappings"]
    found_jumpstart_machine_mode_text_section_mapping = False
    # check that the memory mappings don't overlap
    # the mappings are sorted by the physical address at this point.
    previous_mapping = None
    for mapping in mappings:
        if previous_mapping is None:
            previous_mapping = mapping
            continue

        previous_mapping_size = previous_mapping["page_size"] * previous_mapping["num_pages"]
        if "pma_memory_type" in mapping:
            previous_mapping_size = get_rivos_specific_previous_mapping_size(
                previous_mapping, mapping["pma_memory_type"]
            )

        previous_mapping_end_address = previous_mapping["pa"] + previous_mapping_size

        if mapping["pa"] < previous_mapping_end_address:
            log.error(f"Memory mapping {mapping} overlaps with {previous_mapping}")
            sys.exit(1)

        if "linker_script_section" in mapping and ".jumpstart.text.machine" in mapping[
            "linker_script_section"
        ].split(","):
            # The number of pages in the jumpstart machine mode text section
            # should be a NAPOT value.
            if mapping["num_pages"] & (mapping["num_pages"] - 1) != 0:
                log.error(
                    f"The number of pages in the jumpstart machine mode text section {mapping['num_pages']} is not a NAPOT value."
                )
                sys.exit(1)
            found_jumpstart_machine_mode_text_section_mapping = True

        if (
            diag_attributes["start_test_in_machine_mode"] is True
            and "linker_script_section" in mapping
            and ".text" in mapping["linker_script_section"].split(",")
        ):
            # The text section is machine mode code and should occupy a
            # NAPOT number of pages.
            if mapping["num_pages"] & (mapping["num_pages"] - 1) != 0:
                log.error(
                    f".text is machine mode and it has {mapping['num_pages']} pages which is not a NAPOT number of pages"
                )
                sys.exit(1)

        previous_mapping = mapping

    if found_jumpstart_machine_mode_text_section_mapping is False:
        log.error("Could not find the jumpstart machine mode text section mapping in mappings.")
        sys.exit(1)


def create_pmarr_regions(mappings):
    pmarr_regions = []
    for mapping in mappings:
        if "pma_memory_type" not in mapping:
            if (
                "linker_script_section" in mapping
                and mapping["linker_script_section"]
                == ".jumpstart.text.rcode.init,.jumpstart.text.rcode"
            ):
                continue

            log.error(f"pma_memory_type is not specified in the mapping: {mapping}")
            sys.exit(1)

        mapping_size = mapping["page_size"] * mapping["num_pages"]

        pma_memory_type = mapping["pma_memory_type"]

        matching_pmarr_region = None
        for pmarr_region in pmarr_regions:
            if pmarr_region.can_add_to_region(
                mapping["pa"], mapping["pa"] + mapping_size, pma_memory_type
            ):
                matching_pmarr_region = pmarr_region
                break
        if matching_pmarr_region is None:
            new_pmarr_region = PmarrRegion(
                mapping["pa"], mapping["pa"] + mapping_size, pma_memory_type
            )
            pmarr_regions.append(new_pmarr_region)
        else:
            matching_pmarr_region.add_to_region(mapping["pa"], mapping["pa"] + mapping_size)

    return pmarr_regions


def generate_pmarr_functions(file_descriptor, mappings):
    pmarr_regions = create_pmarr_regions(mappings)

    file_descriptor.write('.section .jumpstart.text.rcode, "ax"\n\n')
    file_descriptor.write("\n")
    file_descriptor.write(".global setup_pmarr\n")
    file_descriptor.write("setup_pmarr:\n\n")

    pmarr_reg_id = 0
    for region in pmarr_regions:
        region.generate_pmarr_region_setup_code(file_descriptor, pmarr_reg_id)
        pmarr_reg_id += 1
        assert pmarr_reg_id < PmarrAttributes.num_registers
    file_descriptor.write("   ret\n\n\n")
    file_descriptor.write("\n")


def generate_rivos_internal_mmu_functions(file_descriptor, mappings):
    generate_pmarr_functions(file_descriptor, mappings)


def generate_uc_end_of_sim_magic_address_function(file_descriptor, uc_end_of_sim_magic_address):
    file_descriptor.write('.section .jumpstart.text.machine, "ax"\n\n')
    file_descriptor.write(".global get_uc_end_of_sim_magic_address\n")
    file_descriptor.write("get_uc_end_of_sim_magic_address:\n\n")

    file_descriptor.write(f"   li a0, {uc_end_of_sim_magic_address}\n")
    file_descriptor.write("   ret\n\n\n")


def generate_rivos_internal_diag_attribute_functions(file_descriptor, diag_attributes):
    generate_uc_end_of_sim_magic_address_function(
        file_descriptor, diag_attributes["uc_end_of_sim_magic_address"]
    )
