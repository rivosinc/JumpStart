#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the diag source files based on the diag attributes file.

import argparse
import logging as log
import math
import os
import sys
from enum import Enum

import public.functions as public_functions
import yaml
from data_structures import BitField, CStruct, DictUtils, ListUtils
from memory_management import (
    AddressType,
    LinkerScript,
    MemoryMapping,
    PageSize,
    PageTableAttributes,
    PageTables,
    TranslationMode,
    TranslationStage,
)
from utils.napot_utils import align_to_napot_size, get_next_napot_size

try:
    import rivos_internal.functions as rivos_internal_functions
except ImportError:
    log.debug("rivos_internal Python module not present.")


class MemoryOp(Enum):
    LOAD = 1
    STORE = 2


def get_memop_of_size(memory_op_type, size_in_bytes):
    if memory_op_type == MemoryOp.LOAD:
        op = "l"
    elif memory_op_type == MemoryOp.STORE:
        op = "s"
    else:
        raise Exception(f"Invalid memory op type: {memory_op_type}")

    if size_in_bytes == 1:
        return op + "b"
    elif size_in_bytes == 2:
        return op + "h"
    elif size_in_bytes == 4:
        return op + "w"
    elif size_in_bytes == 8:
        return op + "d"
    else:
        raise Exception(f"Invalid size: {size_in_bytes} bytes")


class SourceGenerator:
    def __init__(
        self,
        jumpstart_source_attributes_yaml,
        diag_attributes_yaml,
        override_diag_attributes,
        priv_modes_enabled,
    ):
        self.linker_script = None

        self.priv_modes_enabled = None

        self.process_source_attributes(jumpstart_source_attributes_yaml)

        self.priv_modes_enabled = ListUtils.intersection(
            self.jumpstart_source_attributes["priv_modes_supported"],
            priv_modes_enabled,
        )

        self.process_diag_attributes(diag_attributes_yaml, override_diag_attributes)

        self.process_memory_map()

    def process_source_attributes(self, jumpstart_source_attributes_yaml):
        with open(jumpstart_source_attributes_yaml) as f:
            self.jumpstart_source_attributes = yaml.safe_load(f)

        rivos_internal_lib_dir = f"{os.path.dirname(os.path.realpath(__file__))}/rivos_internal"

        if (
            self.jumpstart_source_attributes["rivos_internal_build"] is True
            and os.path.isdir(rivos_internal_lib_dir) is False
        ):
            log.error(
                f"rivos_internal/ not found but rivos_internal_build is set to True in {jumpstart_source_attributes_yaml}"
            )
            sys.exit(1)
        elif (
            self.jumpstart_source_attributes["rivos_internal_build"] is False
            and os.path.isdir(rivos_internal_lib_dir) is True
        ):
            log.warning(
                f"rivos_internal/ exists but rivos_internal_build is set to False in {jumpstart_source_attributes_yaml}"
            )

        # Parse C structs once and store them for later use
        self.c_structs = self._parse_c_structs()

    def process_diag_attributes(self, diag_attributes_yaml, override_diag_attributes):
        self.diag_attributes_yaml = diag_attributes_yaml
        with open(diag_attributes_yaml) as f:
            diag_attributes = yaml.safe_load(f)

        # Override the default diag attribute values with the values
        # specified by the diag.
        DictUtils.override_dict(
            self.jumpstart_source_attributes["diag_attributes"], diag_attributes
        )

        # Set the default diag entry label to start label of the highest privilege mode.
        if self.jumpstart_source_attributes["diag_attributes"]["diag_entry_label"] is None:
            self.jumpstart_source_attributes["diag_attributes"][
                "diag_entry_label"
            ] = f"_{self.priv_modes_enabled[0]}_start"

        if override_diag_attributes is not None:
            # Override the diag attributes with the values specified on the
            # command line.
            cmd_line_diag_attribute_override_dict = DictUtils.create_dict(override_diag_attributes)
            DictUtils.override_dict(
                self.jumpstart_source_attributes["diag_attributes"],
                cmd_line_diag_attribute_override_dict,
            )

        TranslationStage.set_virtualization_enabled(
            self.jumpstart_source_attributes["diag_attributes"]["enable_virtualization"]
        )

        self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"] = int(
            self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"], 2
        )

        active_cpu_mask = self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"]
        if self.jumpstart_source_attributes["diag_attributes"]["primary_cpu_id"] is None:
            # Set the CPU with the lowest CPU ID as the primary CPU.
            self.jumpstart_source_attributes["diag_attributes"]["primary_cpu_id"] = (
                BitField.find_lowest_set_bit(active_cpu_mask)
            )

        self.max_num_cpus_supported = BitField.find_highest_set_bit(active_cpu_mask) + 1

        self.sanity_check_diag_attributes()

        for stage in TranslationStage.get_enabled_stages():
            TranslationStage.set_selected_mode_for_stage(
                stage,
                self.jumpstart_source_attributes["diag_attributes"][
                    f"{TranslationStage.get_atp_register(stage)}_mode"
                ],
            )

    def assign_addresses_to_mapping_for_stage(self, mapping_dict, stage):
        if "page_size" not in mapping_dict:
            raise Exception(f"page_size is not specified for mapping: {mapping_dict}")
        if "pma_memory_type" not in mapping_dict:
            raise Exception(f"pma_memory_type is not specified for mapping: {mapping_dict}")

        # We want to find the next available physical address for the mapping.
        # All the MMUs share the same physical address space so we need to find
        # the next available address that is not already used by another mapping.
        next_available_address = 0
        for target_mmu in MemoryMapping.get_supported_targets():
            if len(self.memory_map[target_mmu][stage]) == 0:
                continue
            temp_address = self.get_next_available_dest_addr_after_last_mapping(
                target_mmu, stage, mapping_dict["page_size"], mapping_dict["pma_memory_type"]
            )
            if temp_address > next_available_address:
                next_available_address = temp_address

        if (
            self.jumpstart_source_attributes["diag_attributes"]["start_test_in_mmode"] is True
            and mapping_dict.get("linker_script_section") is not None
            and ".text" in mapping_dict["linker_script_section"].split(",")
        ):
            # Calculate the total size of the region
            region_size = mapping_dict["page_size"] * mapping_dict["num_pages"]

            # Calculate the NAPOT size that will cover this region
            napot_size = get_next_napot_size(region_size)

            # Align the address to the NAPOT size
            next_available_address = align_to_napot_size(next_available_address, napot_size)

        if self.jumpstart_source_attributes["diag_attributes"]["satp_mode"] != "bare":
            mapping_dict[TranslationStage.get_translates_from(stage)] = next_available_address
        mapping_dict[TranslationStage.get_translates_to(stage)] = next_available_address

        return mapping_dict

    def has_no_addresses(self, mapping_dict):
        """Check if a mapping has no address types set."""
        return not any(
            address_type in mapping_dict and mapping_dict[address_type] is not None
            for address_type in AddressType.get_all_address_types()
        )

    def get_sort_key_for_mapping(self, mapping_dict):
        """Get a sort key for a mapping that sorts by page_size first, then by mappings that don't have addresses."""
        # Get page_size as the first sort criterion
        page_size = mapping_dict.get("page_size", float("inf"))

        if self.has_no_addresses(mapping_dict):
            # Mappings with no addresses come after page_size sorting
            return (
                page_size,
                0,
            )

        # For mappings with addresses, sort by all address types in order
        address_types = AddressType.types
        sort_values = []
        for address_type in address_types:
            value = mapping_dict.get(address_type)
            if value is not None:
                sort_values.append(value)
            else:
                # Use a large number for None values to ensure they sort after valid values
                sort_values.append(float("inf"))

        # Mappings with addresses come after those without (1), then sort by address values
        return (
            page_size,
            1,
        ) + tuple(sort_values)

    def sort_diag_mappings(self):
        return sorted(
            self.jumpstart_source_attributes["diag_attributes"]["mappings"],
            key=self.get_sort_key_for_mapping,
        )

    def add_diag_sections_to_mappings(self):
        for mapping_dict in self.sort_diag_mappings():
            if self.has_no_addresses(mapping_dict):
                if (
                    self.jumpstart_source_attributes["diag_attributes"]["enable_virtualization"]
                    is True
                ):
                    raise ValueError(
                        f"The logic to assign addresses to mappings with no addresses specified in diags that enable virtualization is not implemented yet. Failed on mapping: {mapping_dict}"
                    )
                mapping_dict = self.assign_addresses_to_mapping_for_stage(
                    mapping_dict, TranslationStage.get_enabled_stages()[0]
                )

            for target_mmu in MemoryMapping(mapping_dict, self.max_num_cpus_supported).get_field(
                "target_mmu"
            ):
                # We need a per stage memory mapping object.
                mapping = MemoryMapping(mapping_dict, self.max_num_cpus_supported)

                stage = mapping.get_field("translation_stage")
                mapping.set_field("target_mmu", [target_mmu])

                self.memory_map[target_mmu][stage].append(mapping)

    def process_memory_map(self):
        self.memory_map = {}

        for supported_mmu in MemoryMapping.get_supported_targets():
            self.memory_map[supported_mmu] = {}
            for stage in TranslationStage.get_enabled_stages():
                self.memory_map[supported_mmu][stage] = []

        self.add_jumpstart_sections_to_mappings()

        self.add_diag_sections_to_mappings()

        for target_mmu in self.memory_map.keys():
            for stage in self.memory_map[target_mmu].keys():
                # Sort all the mappings by the destination address.
                self.memory_map[target_mmu][stage] = sorted(
                    self.memory_map[target_mmu][stage],
                    key=lambda x: x.get_field(TranslationStage.get_translates_to(stage)),
                    reverse=False,
                )

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal_functions.process_cpu_memory_map(
                self.memory_map["cpu"], self.jumpstart_source_attributes
            )

        self.sanity_check_memory_map()

        self.create_page_tables_data()

    def create_page_tables_data(self):
        self.page_tables = {}
        for target_mmu in MemoryMapping.get_supported_targets():
            if target_mmu not in self.memory_map:
                # Don't create page tables for MMUs that don't have any
                # mappings.
                continue

            self.page_tables[target_mmu] = {}

            for stage in TranslationStage.get_enabled_stages():
                translation_mode = TranslationStage.get_selected_mode_for_stage(stage)
                if translation_mode == "bare":
                    # No pagetable mappings for the bare mode.
                    continue

                self.page_tables[target_mmu][stage] = PageTables(
                    translation_mode,
                    self.jumpstart_source_attributes["diag_attributes"][
                        "max_num_pagetable_pages_per_stage"
                    ],
                    self.memory_map[target_mmu][stage],
                )

    def sanity_check_memory_map(self):
        public_functions.sanity_check_memory_map(self.memory_map["cpu"])

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal_functions.sanity_check_memory_map(
                self.jumpstart_source_attributes["diag_attributes"], self.memory_map
            )

    def add_pagetable_mappings(self, start_address):
        assert (
            start_address is not None and start_address >= 0
        ), f"Invalid start address for pagetables: {start_address}"

        common_attributes = {
            "page_size": PageSize.SIZE_4K,
            "num_pages": self.jumpstart_source_attributes["diag_attributes"][
                "max_num_pagetable_pages_per_stage"
            ],
            "umode": "0b0",
            "pma_memory_type": "wb",
        }
        if (
            self.jumpstart_source_attributes["diag_attributes"]["allow_page_table_modifications"]
            is True
        ):
            common_attributes["xwr"] = "0b011"
        else:
            common_attributes["xwr"] = "0b001"

        for target_mmu in MemoryMapping.get_supported_targets():
            if target_mmu not in self.memory_map:
                # Don't add pagetable mappings for MMUs that
                # don't have any mappings.
                continue

            per_stage_pagetable_mappings = {}

            for stage in TranslationStage.get_enabled_stages():
                translation_mode = TranslationStage.get_selected_mode_for_stage(stage)
                if translation_mode == "bare":
                    # No pagetable mappings for the bare mode.
                    continue

                section_mapping = common_attributes.copy()
                source_address_type = TranslationStage.get_translates_from(stage)
                dest_address_type = TranslationStage.get_translates_to(stage)

                # The start of the pagetables have to be aligned to the size of the
                # root (first level) page table.
                root_page_table_size = PageTableAttributes.mode_attributes[translation_mode][
                    "pagetable_sizes"
                ][0]
                if (start_address % root_page_table_size) != 0:
                    start_address = (
                        math.floor(start_address / root_page_table_size) + 1
                    ) * root_page_table_size

                section_mapping[source_address_type] = section_mapping[dest_address_type] = (
                    start_address
                )

                section_mapping["translation_stage"] = stage
                section_mapping["linker_script_section"] = (
                    f".jumpstart.{target_mmu}.rodata.{stage}_stage.pagetables"
                )
                section_mapping["target_mmu"] = [target_mmu]

                per_stage_pagetable_mappings[stage] = MemoryMapping(
                    section_mapping, self.max_num_cpus_supported
                )

                self.memory_map[target_mmu][stage].insert(
                    len(self.memory_map[target_mmu][stage]), per_stage_pagetable_mappings[stage]
                )

                start_address += common_attributes["num_pages"] * common_attributes["page_size"]

            if "g" in TranslationStage.get_enabled_stages():
                vs_stage_memory_mapping = per_stage_pagetable_mappings["vs"].copy()

                vs_stage_memory_mapping.set_field("translation_stage", "g")

                mapping_address = vs_stage_memory_mapping.get_field(
                    TranslationStage.get_translates_to("vs")
                )
                vs_stage_memory_mapping.set_field(TranslationStage.get_translates_from("vs"), None)
                vs_stage_memory_mapping.set_field(TranslationStage.get_translates_to("vs"), None)
                vs_stage_memory_mapping.set_field(
                    TranslationStage.get_translates_from("g"), mapping_address
                )
                vs_stage_memory_mapping.set_field(
                    TranslationStage.get_translates_to("g"), mapping_address
                )

                vs_stage_memory_mapping.set_field("umode", 1)

                self.memory_map[target_mmu]["g"].insert(
                    len(self.memory_map[target_mmu]["g"]), vs_stage_memory_mapping
                )

            # Adds G-stage pagetable memory region into hs stage memory map to
            # allow HS-mode to access G-stage pagetables.
            if target_mmu == "cpu" and "g" in TranslationStage.get_enabled_stages():
                mapping = per_stage_pagetable_mappings["g"].copy()
                mapping.set_field("translation_stage", "hs")
                mapping.set_field("va", mapping.get_field("gpa"))
                mapping.set_field("pa", mapping.get_field("spa"))
                mapping.set_field("gpa", None)
                mapping.set_field("spa", None)
                self.memory_map[target_mmu]["hs"].insert(
                    len(self.memory_map[target_mmu]["hs"]), mapping
                )

            # Adds VS-stage pagetable memory region into hs stage memory map to
            # allow HS-mode to access VS-stage pagetables.
            if target_mmu == "cpu" and "vs" in TranslationStage.get_enabled_stages():
                mapping = per_stage_pagetable_mappings["vs"].copy()
                mapping.set_field("translation_stage", "hs")
                mapping.set_field("pa", mapping.get_field("gpa"))
                mapping.set_field("gpa", None)
                self.memory_map[target_mmu]["hs"].insert(
                    len(self.memory_map[target_mmu]["hs"]), mapping
                )

    def add_jumpstart_sections_to_mappings(self):
        target_mmu = "cpu"
        pagetables_start_address = 0

        for stage in TranslationStage.get_enabled_stages():
            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                self.memory_map[target_mmu][stage].extend(
                    rivos_internal_functions.get_additional_mappings(
                        target_mmu,
                        stage,
                        self.jumpstart_source_attributes,
                    )
                )

            for mode in self.priv_modes_enabled:
                self.add_jumpstart_cpu_mode_mappings(target_mmu, stage, mode)

            # We will place the pagetables for all MMUs after the last
            # physical address used by the CPU jumpstart mappings.
            next_available_dest_address = self.get_next_available_dest_addr_after_last_mapping(
                target_mmu, stage, PageSize.SIZE_4K, "wb"
            )
            if next_available_dest_address > pagetables_start_address:
                pagetables_start_address = next_available_dest_address

        self.add_pagetable_mappings(pagetables_start_address)

    def sanity_check_diag_attributes(self):
        for stage in TranslationStage.get_enabled_stages():
            atp_register = TranslationStage.get_atp_register(stage)
            assert f"{atp_register}_mode" in self.jumpstart_source_attributes["diag_attributes"]
            assert TranslationMode.is_valid_mode(
                self.jumpstart_source_attributes["diag_attributes"][f"{atp_register}_mode"]
            )

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal_functions.sanity_check_diag_attributes(
                self.jumpstart_source_attributes["diag_attributes"]
            )

        assert (
            self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"].bit_count()
            <= self.max_num_cpus_supported
        )
        primary_cpu_id = int(self.jumpstart_source_attributes["diag_attributes"]["primary_cpu_id"])
        assert (
            self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"]
            & (1 << primary_cpu_id)
        ) != 0

    def get_next_available_dest_addr_after_last_mapping(
        self, target_mmu, stage, page_size, pma_memory_type
    ):
        assert len(self.memory_map[target_mmu][stage]) > 0, "No previous mappings found."

        previous_mapping_id = len(self.memory_map[target_mmu][stage]) - 1
        previous_mapping = self.memory_map[target_mmu][stage][previous_mapping_id]

        previous_mapping_size = previous_mapping.get_field(
            "page_size"
        ) * previous_mapping.get_field("num_pages")
        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            previous_mapping_size = rivos_internal_functions.get_previous_mapping_size(
                previous_mapping, pma_memory_type
            )

        dest_address_type = TranslationStage.get_translates_to(stage)
        next_available_pa = previous_mapping.get_field(dest_address_type) + previous_mapping_size

        if (next_available_pa % page_size) != 0:
            # Align the PA to the page size.
            next_available_pa = (math.floor(next_available_pa / page_size) + 1) * page_size

        return next_available_pa

    def add_jumpstart_cpu_mode_mappings(self, cpu_mmu, stage, mode):
        area_name = f"jumpstart_{mode}"
        area_start_address_attribute_name = f"{mode}_start_address"

        # We pick up the start PA of the area from the diag_attributes
        #   Example: mmode_start_address, smode_start_address,
        #            umode_start_address
        # If this attribute is not null we use it to set up the address of the
        # first section in the area. Every subsequent section will just follow
        # the previous section in the PA space.
        area_start_pa = None
        if (
            area_start_address_attribute_name in self.jumpstart_source_attributes["diag_attributes"]
            and self.jumpstart_source_attributes["diag_attributes"][
                area_start_address_attribute_name
            ]
            is not None
        ):
            area_start_pa = self.jumpstart_source_attributes["diag_attributes"][
                area_start_address_attribute_name
            ]

        for section_name in self.jumpstart_source_attributes[area_name]:
            section_mapping = self.jumpstart_source_attributes[area_name][section_name].copy()
            section_mapping["target_mmu"] = [cpu_mmu]
            section_mapping["translation_stage"] = stage

            if TranslationStage.get_selected_mode_for_stage(stage) == "bare":
                section_mapping["no_pte_allocation"] = True
                section_mapping.pop("xwr", None)
                section_mapping.pop("umode", None)

            for attribute in ["num_pages", "page_size", "num_pages_per_cpu"]:
                # This is where we allow the diag to override the attributes of jumpstart sections.
                # We can change the page size and num_pages of the section.
                #   Example: num_pages_for_jumpstart_smode_bss, num_pages_for_jumpstart_mmode_rodata,
                #            num_pages_per_cpu_for_jumpstart_smode_bss, etc.
                attribute_name = f"{attribute}_for_{area_name}_{section_name}"
                if (
                    attribute in section_mapping
                    and attribute_name in self.jumpstart_source_attributes["diag_attributes"]
                ):
                    raise Exception(
                        f"{attribute} specified for {section_name} in {area_name} and {attribute_name} specified in diag_attributes."
                    )

                if attribute_name in self.jumpstart_source_attributes["diag_attributes"]:
                    section_mapping[attribute] = self.jumpstart_source_attributes[
                        "diag_attributes"
                    ][attribute_name]

            dest_address_type = TranslationStage.get_translates_to(stage)
            assert dest_address_type not in section_mapping
            if area_start_pa is not None:
                section_mapping[dest_address_type] = area_start_pa
                # Every subsequent section will just follow the previous section
                # in the PA space.
                area_start_pa = None
            else:
                # We're going to start the PA of the new mapping after the PA range
                # of the last mapping.
                section_mapping[dest_address_type] = (
                    self.get_next_available_dest_addr_after_last_mapping(
                        cpu_mmu,
                        stage,
                        section_mapping["page_size"],
                        section_mapping.get("pma_memory_type", None),
                    )
                )

            if section_mapping.get("alignment", None) is not None:
                section_mapping[dest_address_type] = (
                    section_mapping[dest_address_type] + section_mapping["alignment"] - 1
                ) & ~(section_mapping["alignment"] - 1)

            if (
                "no_pte_allocation" not in section_mapping
                or section_mapping["no_pte_allocation"] is False
            ):
                # This is the only real use for the "no_pte_allocation" attribute.
                # If we had another way to tell that we had to copy the VA from
                # the PA for these mappings we could remove this attribute.
                section_mapping[TranslationStage.get_translates_from(stage)] = section_mapping[
                    dest_address_type
                ]

                if stage == "g":
                    # For G-stage address translation, all memory accesses
                    # (including those made to access data structures for
                    # VS-stage address translation) are considered to be
                    # #user-level accesses, as though executed in U-mode.
                    section_mapping["umode"] = "0b1"

            if section_mapping.get("num_pages") == 0:
                continue

            self.memory_map[cpu_mmu][stage].insert(
                len(self.memory_map[cpu_mmu][stage]),
                MemoryMapping(section_mapping, self.max_num_cpus_supported),
            )

    def generate_linker_script(self, output_linker_script):
        self.linker_script = LinkerScript(
            entry_label=self.jumpstart_source_attributes["diag_attributes"]["diag_entry_label"],
            elf_address_range=(
                self.jumpstart_source_attributes["diag_attributes"]["elf_start_address"],
                self.jumpstart_source_attributes["diag_attributes"]["elf_end_address"],
            ),
            mappings=self.memory_map["cpu"],
            attributes_file=self.diag_attributes_yaml,
        )
        self.linker_script.generate(output_linker_script)

    def generate_defines_file(self, output_defines_file):
        with open(output_defines_file, "w") as file_descriptor:
            file_descriptor.write(
                f"// This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

            file_descriptor.write("\n// Jumpstart Attributes defines\n\n")
            for define_name in self.jumpstart_source_attributes["defines"]:
                file_descriptor.write(f"#ifndef {define_name}\n")
                define_value = self.jumpstart_source_attributes["defines"][define_name]
                # Write all integers as hexadecimal for consistency and C/Assembly compatibility
                if isinstance(define_value, int):
                    file_descriptor.write(f"#define {define_name} 0x{define_value:x}\n")
                else:
                    file_descriptor.write(f"#define {define_name} {define_value}\n")
                file_descriptor.write("#endif\n")
            file_descriptor.write("\n")

            file_descriptor.write(
                f"#define MAX_NUM_CPUS_SUPPORTED {self.max_num_cpus_supported}\n\n"
            )

            for mod in self.priv_modes_enabled:
                file_descriptor.write(f"#define {mod.upper()}_MODE_ENABLED 1\n")

            file_descriptor.write("\n// Jumpstart Syscall Numbers defines\n\n")
            current_syscall_number = 0
            for syscall_name in self.jumpstart_source_attributes["syscall_numbers"]:
                file_descriptor.write(f"#define {syscall_name} {current_syscall_number}\n")
                current_syscall_number += 1

            file_descriptor.write("\n// Diag Attributes defines\n\n")
            # Perform some transformations so that we can print them as defines.
            diag_attributes = self.jumpstart_source_attributes["diag_attributes"].copy()

            for stage in TranslationStage.get_enabled_stages():
                atp_register = TranslationStage.get_atp_register(stage)
                diag_attributes[f"{atp_register}_mode"] = TranslationMode.get_encoding(
                    TranslationStage.get_selected_mode_for_stage(stage)
                )

            for attribute in diag_attributes:
                if isinstance(diag_attributes[attribute], bool):
                    file_descriptor.write(f"#ifndef {attribute.upper()}\n")
                    file_descriptor.write(
                        f"#define {attribute.upper()} {int(diag_attributes[attribute])}\n"
                    )
                    file_descriptor.write("#endif\n")
                elif isinstance(diag_attributes[attribute], int):
                    file_descriptor.write(f"#ifndef {attribute.upper()}\n")
                    file_descriptor.write(
                        f"#define {attribute.upper()} {hex(diag_attributes[attribute])}\n"
                    )
                    file_descriptor.write("#endif\n")

            # Generate stack-related defines
            self.generate_stack_defines(file_descriptor)

            # Generate register context save/restore defines
            self.generate_reg_context_save_restore_defines(file_descriptor)

            # Generate C structs defines
            self.generate_cstructs_defines(file_descriptor)

            # Generate rivos internal defines if this is a rivos internal build
            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                rivos_internal_functions.add_rivos_internal_defines(
                    file_descriptor, self.jumpstart_source_attributes
                )

            file_descriptor.close()

    def generate_data_structures_file(self, output_data_structures_file):
        with open(output_data_structures_file, "w") as file_descriptor:
            file_descriptor.write(
                f"// This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )
            file_descriptor.write("#pragma once\n\n")

            # Only include these headers in C code.
            file_descriptor.write("#if !defined(__ASSEMBLER__) && !defined(__ASSEMBLY__)\n\n")

            file_descriptor.write("\n\n")
            file_descriptor.write("#include <inttypes.h>\n")
            file_descriptor.write("#include <stddef.h>\n\n")

            # Generate C struct definitions
            self.generate_cstructs_data_structures(file_descriptor)

            file_descriptor.write(
                "#endif /* !defined(__ASSEMBLER__) && !defined(__ASSEMBLY__) */\n\n"
            )

            file_descriptor.close()

    def find_memory_mapping_by_linker_section(self, linker_script_section, target_mmu=None):
        """Find a MemoryMapping object by its linker_script_section name.

        Args:
            linker_script_section (str): The linker script section name to search for
            target_mmu (str, optional): The target MMU to search in. If None, searches all target MMUs.

        Returns:
            MemoryMapping or None: The found MemoryMapping object, or None if not found
        """
        target_mmus_to_search = [target_mmu] if target_mmu is not None else self.memory_map.keys()

        for mmu in target_mmus_to_search:
            if mmu not in self.memory_map:
                continue
            for stage in self.memory_map[mmu].keys():
                for mapping in self.memory_map[mmu][stage]:
                    if mapping.get_field("linker_script_section") == linker_script_section:
                        return mapping
        return None

    def generate_stack_defines(self, file_descriptor):
        # This is a bit of a mess. Both mmode and smode share the same stack.
        # We've named this stack "privileged" so we need to map the stack
        # name to the mode.
        stack_types = ListUtils.intersection(["umode"], self.priv_modes_enabled)
        stack_types.append("privileged")

        for stack_type in stack_types:
            # Make sure we can equally distribute the number of total stack pages
            # among the cpus.

            # Find the MemoryMapping object for this stack type
            linker_section = f".jumpstart.cpu.stack.{stack_type}"
            stack_mapping = self.find_memory_mapping_by_linker_section(linker_section, "cpu")
            if stack_mapping is None:
                raise Exception(
                    f"MemoryMapping with linker_script_section '{linker_section}' not found in memory_map"
                )

            # Get the num_pages from the MemoryMapping object
            num_pages_for_stack = stack_mapping.get_field("num_pages")
            stack_page_size = stack_mapping.get_field("page_size")

            assert num_pages_for_stack % self.max_num_cpus_supported == 0
            num_pages_per_cpu_for_stack = int(num_pages_for_stack / self.max_num_cpus_supported)

            file_descriptor.write(
                f"#define NUM_PAGES_PER_CPU_FOR_{stack_type.upper()}_STACK {num_pages_per_cpu_for_stack}\n\n"
            )

            file_descriptor.write(
                f"#define {stack_type.upper()}_STACK_PAGE_SIZE {stack_page_size}\n\n"
            )

    def generate_stack(self, file_descriptor):
        # This is a bit of a mess. Both mmode and smode share the same stack.
        # We've named this stack "privileged" so we need to map the stack
        # name to the mode.
        stack_types = ListUtils.intersection(["umode"], self.priv_modes_enabled)
        stack_types.append("privileged")

        for stack_type in stack_types:
            # Make sure we can equally distribute the number of total stack pages
            # among the cpus.

            # Find the MemoryMapping object for this stack type
            linker_section = f".jumpstart.cpu.stack.{stack_type}"
            stack_mapping = self.find_memory_mapping_by_linker_section(linker_section, "cpu")
            if stack_mapping is None:
                raise Exception(
                    f"MemoryMapping with linker_script_section '{linker_section}' not found in memory_map"
                )

            # Get the num_pages from the MemoryMapping object
            num_pages_for_stack = stack_mapping.get_field("num_pages")
            stack_page_size = stack_mapping.get_field("page_size")

            assert num_pages_for_stack % self.max_num_cpus_supported == 0
            num_pages_per_cpu_for_stack = int(num_pages_for_stack / self.max_num_cpus_supported)

            file_descriptor.write(f'.section .jumpstart.cpu.stack.{stack_type}, "aw"\n')
            # Calculate alignment based on page size (log2 of page size)
            alignment = stack_page_size.bit_length() - 1
            file_descriptor.write(f".align {alignment}\n")
            file_descriptor.write(f".global {stack_type}_stack_top\n")
            file_descriptor.write(f"{stack_type}_stack_top:\n")
            for i in range(self.max_num_cpus_supported):
                file_descriptor.write(f".global {stack_type}_stack_top_cpu_{i}\n")
                file_descriptor.write(f"{stack_type}_stack_top_cpu_{i}:\n")
                file_descriptor.write(f"  .zero {num_pages_per_cpu_for_stack * stack_page_size}\n")
            file_descriptor.write(f".global {stack_type}_stack_bottom\n")
            file_descriptor.write(f"{stack_type}_stack_bottom:\n\n")

    def generate_cpu_sync_functions(self, file_descriptor):
        active_cpu_mask = self.jumpstart_source_attributes["diag_attributes"]["active_cpu_mask"]

        modes = ListUtils.intersection(["mmode", "smode"], self.priv_modes_enabled)
        for mode in modes:
            file_descriptor.write(
                f"""
.section .jumpstart.cpu.text.{mode}, "ax"
# Inputs:
#   a0: cpu mask of cpus to sync.
#   a1: sync point address (4 byte aligned)
.global sync_cpus_in_mask_from_{mode}
sync_cpus_in_mask_from_{mode}:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  CHECKTC_DISABLE

  GET_THREAD_ATTRIBUTES_CPU_ID(t0)
  # Get the lowest numbered cpu id in the mask to use as the primary cpu
  # to drive the sync.
  ctz t1, a0

  li t4, 1
  sll t5, t4, t0
  sll t4, t4, t1

  # Both this cpu id and the primary cpu id should be part of
  # the mask of cpus to sync
  and t3, t5, a0
  beqz t3, jumpstart_{mode}_fail
  and t3, t4, a0
  beqz t3, jumpstart_{mode}_fail

  amoor.w.aqrl t3, t5, (a1)

  # This bit should not be already set.
  and t3, t3, t5
  bnez t3, jumpstart_{mode}_fail

  bne t4, t5, wait_for_primary_cpu_to_clear_sync_point_bits_{mode}

wait_for_all_cpus_to_set_sync_point_bits_{mode}:
  # Primary cpu waits till all the cpus have set their bits in the sync point.
  # twiddle thumbs to avoid excessive spinning
  pause
  lw t4, (a1)
  bne t4, a0, wait_for_all_cpus_to_set_sync_point_bits_{mode}

  amoswap.w t4, zero, (a1)

  bne t4, a0, jumpstart_{mode}_fail

  j return_from_sync_cpus_in_mask_from_{mode}

wait_for_primary_cpu_to_clear_sync_point_bits_{mode}:
  # non-primary cpus wait for the primary cpu to clear the sync point bits.
  # twiddle thumbs to avoid excessive spinning
  pause
  lw t4, (a1)
  srl t4, t4, t0
  andi t4, t4, 1
  bnez t4, wait_for_primary_cpu_to_clear_sync_point_bits_{mode}

return_from_sync_cpus_in_mask_from_{mode}:
  CHECKTC_ENABLE

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global sync_all_cpus_from_{mode}
sync_all_cpus_from_{mode}:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  li a0, {active_cpu_mask}
  la a1, cpu_sync_point

  jal sync_cpus_in_mask_from_{mode}

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret
"""
            )

    def generate_smode_fail_functions(self, file_descriptor):
        if "smode" in self.priv_modes_enabled:
            file_descriptor.write('.section .jumpstart.cpu.text.smode, "ax"\n\n')
            file_descriptor.write(".global jumpstart_smode_fail\n")
            file_descriptor.write("jumpstart_smode_fail:\n")

            if "mmode" in self.priv_modes_enabled:
                # use jumpstart mmode env call
                file_descriptor.write("  li  a0, DIAG_FAILED\n")
                file_descriptor.write("  j exit_from_smode\n")
            else:
                # We expect to be running in sbi_firmware_boot mode.
                # Use sbi call to request mmode fw to shutdown system.
                file_descriptor.write("  li  a0, 0\n")
                file_descriptor.write("  li  a1, DIAG_FAILED\n")
                file_descriptor.write("  jal sbi_system_reset\n")

    def generate_mmu_functions(self, file_descriptor):
        modes = ListUtils.intersection(["mmode", "smode"], self.priv_modes_enabled)
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.cpu.text.{mode}, "ax"\n\n')
            file_descriptor.write(f".global setup_mmu_from_{mode}\n")
            file_descriptor.write(f"setup_mmu_from_{mode}:\n\n")
            for stage in TranslationStage.get_enabled_stages():
                atp_register = TranslationStage.get_atp_register(stage)
                file_descriptor.write(f"    li   t0, {atp_register.upper()}_MODE\n")
                file_descriptor.write(f"    slli  t0, t0, {atp_register.upper()}64_MODE_SHIFT\n")
                if stage in self.page_tables["cpu"]:
                    file_descriptor.write(
                        f"    la t1, {self.page_tables['cpu'][stage].get_asm_label()}\n"
                    )
                    file_descriptor.write("    srai t1, t1, PAGE_OFFSET\n")
                    file_descriptor.write("    add  t0, t1, t0\n")
                else:
                    assert TranslationStage.get_selected_mode_for_stage(stage) == "bare"
                file_descriptor.write(f"    csrw  {atp_register}, t0\n")

            file_descriptor.write("    sfence.vma\n")
            if self.jumpstart_source_attributes["diag_attributes"]["enable_virtualization"] is True:
                # This is for the hgatp update.
                file_descriptor.write("    hfence.gvma\n")
            file_descriptor.write("    ret\n")

    def generate_page_tables(self, file_descriptor):
        for target_mmu in MemoryMapping.get_supported_targets():
            if target_mmu not in self.page_tables:
                continue

            for stage in TranslationStage.get_enabled_stages():
                if stage not in self.page_tables[target_mmu]:
                    continue

                file_descriptor.write(
                    f'.section .jumpstart.{target_mmu}.rodata.{stage}_stage.pagetables, "a"\n\n'
                )

                file_descriptor.write(
                    f".global {self.page_tables[target_mmu][stage].get_asm_label()}\n"
                )
                file_descriptor.write(f"{self.page_tables[target_mmu][stage].get_asm_label()}:\n\n")

                file_descriptor.write("/* Memory mappings in this page table:\n")
                for mapping in self.page_tables[target_mmu][stage].get_mappings():
                    if not mapping.is_bare_mapping():
                        file_descriptor.write(f"{mapping}\n")
                file_descriptor.write("*/\n")

                pte_size_in_bytes = self.page_tables[target_mmu][stage].get_attribute(
                    "pte_size_in_bytes"
                )
                last_filled_address = None
                for address in list(
                    sorted(self.page_tables[target_mmu][stage].get_pte_addresses())
                ):
                    if last_filled_address is not None and address != (
                        last_filled_address + pte_size_in_bytes
                    ):
                        file_descriptor.write(
                            f".skip {hex(address - (last_filled_address + pte_size_in_bytes))}\n"
                        )
                    log.debug(
                        f"Writing [{hex(address)}] = {hex(self.page_tables[target_mmu][stage].get_pte(address))}"
                    )
                    file_descriptor.write(f"\n# [{hex(address)}]\n")
                    file_descriptor.write(
                        f".{pte_size_in_bytes}byte {hex(self.page_tables[target_mmu][stage].get_pte(address))}\n"
                    )

                    last_filled_address = address

    def generate_assembly_file(self, output_assembly_file):
        with open(output_assembly_file, "w") as file:
            file.write(
                f"# This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

            file.write("\n\n")
            file.write('#include "cpu_bits.h"\n\n')

            self.generate_mmu_functions(file)

            self.generate_smode_fail_functions(file)

            self.generate_cpu_sync_functions(file)

            self.generate_stack(file)

            self.generate_thread_attributes_code(file)

            self.generate_reg_context_save_restore_assembly(file)

            self.generate_cstructs_assembly(file)

            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                rivos_internal_functions.generate_rivos_internal_mmu_functions(
                    file, self.priv_modes_enabled
                )

            self.generate_page_tables(file)

            file.close()

    def generate_thread_attributes_code(self, file_descriptor):
        self.generate_thread_attributes_getter_functions(file_descriptor)

        modes = ListUtils.intersection(["smode", "mmode"], self.priv_modes_enabled)
        mode_encodings = {"smode": "PRV_S", "mmode": "PRV_M"}
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.cpu.text.{mode}.init, "ax"\n')
            file_descriptor.write("# Inputs:\n")
            file_descriptor.write("#   a0: cpu id\n")
            file_descriptor.write("#   a1: physical cpu id\n")
            file_descriptor.write(f".global setup_thread_attributes_from_{mode}\n")
            file_descriptor.write(f"setup_thread_attributes_from_{mode}:\n")
            file_descriptor.write("  li t1, MAX_NUM_CPUS_SUPPORTED\n")
            file_descriptor.write(f"  bgeu a0, t1, jumpstart_{mode}_fail\n")
            file_descriptor.write("\n")
            # Save input parameters and return address to stack
            file_descriptor.write("  addi sp, sp, -24\n")
            file_descriptor.write("  sd a0, 0(sp)    # Save cpu_id\n")
            file_descriptor.write("  sd a1, 8(sp)    # Save physical_cpu_id\n")
            file_descriptor.write("  sd ra, 16(sp)   # Save return address\n")
            file_descriptor.write("\n")
            # Call getter function to get thread attributes address for this cpu id
            file_descriptor.write(f"  jal get_thread_attributes_for_cpu_id_from_{mode}\n")
            file_descriptor.write("  mv tp, a0       # Move returned address to tp\n")
            file_descriptor.write("\n")
            # Restore parameters from stack
            file_descriptor.write("  ld ra, 16(sp)   # Restore return address\n")
            file_descriptor.write("  ld a1, 8(sp)    # Restore physical_cpu_id\n")
            file_descriptor.write("  ld a0, 0(sp)    # Restore cpu_id\n")
            file_descriptor.write("  addi sp, sp, 24\n")
            file_descriptor.write("\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_CPU_ID(a0)\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_PHYSICAL_CPU_ID(a1)\n")
            file_descriptor.write("\n")
            file_descriptor.write("  li t0, TRAP_OVERRIDE_ATTRIBUTES_STRUCT_SIZE_IN_BYTES\n")
            file_descriptor.write("  mul t0, a0, t0\n")
            file_descriptor.write("  la t1, trap_override_attributes_region\n")
            file_descriptor.write("  add t0, t1, t0\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_TRAP_OVERRIDE_STRUCT_ADDRESS(t0)\n")
            file_descriptor.write("\n")
            file_descriptor.write(
                "  li t0, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES * MAX_NUM_CONTEXT_SAVES\n"
            )
            file_descriptor.write("  mul t0, a0, t0\n")
            file_descriptor.write("\n")
            if "mmode" in modes:
                file_descriptor.write("  la t1, mmode_reg_context_save_region\n")
                file_descriptor.write("  add t1, t1, t0\n")
                file_descriptor.write("  la t2, mmode_reg_context_save_region_end\n")
                file_descriptor.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
                file_descriptor.write(
                    "  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
                )
                file_descriptor.write("  li t1, MAX_NUM_CONTEXT_SAVES\n")
                file_descriptor.write(
                    "  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_MMODE(t1)\n"
                )
                file_descriptor.write("\n")

                file_descriptor.write("  csrr t1, marchid\n")
                file_descriptor.write("  SET_THREAD_ATTRIBUTES_MARCHID(t1)\n")
                file_descriptor.write("  csrr t1, mimpid\n")
                file_descriptor.write("  SET_THREAD_ATTRIBUTES_MIMPID(t1)\n")
                file_descriptor.write("\n")

            if "smode" in modes:
                file_descriptor.write("  la t1, smode_reg_context_save_region\n")
                file_descriptor.write("  add t1, t1, t0\n")
                file_descriptor.write("  la t2, smode_reg_context_save_region_end\n")
                file_descriptor.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
                file_descriptor.write(
                    "  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
                )

            file_descriptor.write("  li t1, MAX_NUM_CONTEXT_SAVES\n")
            file_descriptor.write(
                "  SET_THREAD_ATTRIBUTES_NUM_CONTEXT_SAVES_REMAINING_IN_SMODE(t1)\n"
            )
            file_descriptor.write("\n")
            file_descriptor.write("  li  t0, 0\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_VSMODE_SETUP_DONE(t0)\n")
            file_descriptor.write("\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_CURRENT_V_BIT(t0)\n")
            file_descriptor.write("\n")
            file_descriptor.write(f"  li  t0, {mode_encodings[mode]}\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)\n")
            file_descriptor.write("\n")
            file_descriptor.write("  li  t0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE\n")
            file_descriptor.write("  SET_THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER(t0)\n")
            file_descriptor.write("\n")
            file_descriptor.write("  ret\n")

    def generate_thread_attributes_getter_functions(self, file_descriptor):
        """Generate functions to get thread attributes struct address for a given CPU ID."""
        modes = ListUtils.intersection(["smode", "mmode"], self.priv_modes_enabled)
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.cpu.text.{mode}.init, "ax"\n')
            file_descriptor.write("# Inputs:\n")
            file_descriptor.write("#   a0: cpu id\n")
            file_descriptor.write("# Outputs:\n")
            file_descriptor.write(
                "#   a0: address of thread attributes struct for the given cpu id\n"
            )
            file_descriptor.write(f".global get_thread_attributes_for_cpu_id_from_{mode}\n")
            file_descriptor.write(f"get_thread_attributes_for_cpu_id_from_{mode}:\n")
            file_descriptor.write("  li t1, MAX_NUM_CPUS_SUPPORTED\n")
            file_descriptor.write(f"  bgeu a0, t1, jumpstart_{mode}_fail\n")
            file_descriptor.write("\n")
            file_descriptor.write("  li  t2, THREAD_ATTRIBUTES_STRUCT_SIZE_IN_BYTES\n")
            file_descriptor.write("  mul t2, a0, t2\n")
            file_descriptor.write("  la  t1, thread_attributes_region\n")
            file_descriptor.write("  add a0, t1, t2\n")
            file_descriptor.write("  ret\n\n")

    def generate_reg_context_save_restore_defines(self, file_descriptor):
        """Generate defines for register context save/restore functionality."""
        assert (
            self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
                "temp_register"
            ]
            not in self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
                "registers"
            ]["gprs"]
        )

        num_registers = 0
        for reg_type in self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
            "registers"
        ]:
            reg_names = self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
                "registers"
            ][reg_type]
            for reg_name in reg_names:
                file_descriptor.write(
                    f"#define {reg_name.upper()}_OFFSET_IN_SAVE_REGION ({num_registers} * 8)\n"
                )
                num_registers += 1

        temp_reg_name = self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
            "temp_register"
        ]

        file_descriptor.write(
            f"\n#define REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES ({num_registers} * 8)\n"
        )
        file_descriptor.write(
            f"\n#define MAX_NUM_CONTEXT_SAVES {self.jumpstart_source_attributes['reg_context_to_save_across_exceptions']['max_num_context_saves']}\n"
        )

        file_descriptor.write("\n#define SAVE_ALL_GPRS   ;")
        for gpr_name in self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
            "registers"
        ]["gprs"]:
            file_descriptor.write(
                f"\\\n  sd {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;"
            )
        file_descriptor.write("\n\n")

        file_descriptor.write("\n#define RESTORE_ALL_GPRS   ;")
        for gpr_name in self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
            "registers"
        ]["gprs"]:
            file_descriptor.write(
                f"\\\n  ld {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;"
            )
        file_descriptor.write("\n\n")

    def generate_reg_context_save_restore_assembly(self, file_descriptor):
        """Generate assembly code for register context save/restore regions."""
        num_registers = 0
        for reg_type in self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
            "registers"
        ]:
            reg_names = self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
                "registers"
            ][reg_type]
            for reg_name in reg_names:
                num_registers += 1

        file_descriptor.write('\n\n.section .jumpstart.cpu.data.privileged, "a"\n')
        modes = ListUtils.intersection(["mmode", "smode"], self.priv_modes_enabled)
        file_descriptor.write(
            f"\n# {modes} context saved registers:\n# {self.jumpstart_source_attributes['reg_context_to_save_across_exceptions']['registers']}\n"
        )
        for mode in modes:
            file_descriptor.write(f".global {mode}_reg_context_save_region\n")
            file_descriptor.write(f"{mode}_reg_context_save_region:\n")
            for i in range(self.max_num_cpus_supported):
                file_descriptor.write(
                    f"  # {mode} context save area for cpu {i}'s {num_registers} registers. {self.jumpstart_source_attributes['reg_context_to_save_across_exceptions']['max_num_context_saves']} nested contexts supported.\n"
                )
                for i in range(
                    self.jumpstart_source_attributes["reg_context_to_save_across_exceptions"][
                        "max_num_context_saves"
                    ]
                ):
                    f"  # Context {i}\n"
                    file_descriptor.write(f"  .zero {num_registers * 8}\n\n")
            file_descriptor.write(f".global {mode}_reg_context_save_region_end\n")
            file_descriptor.write(f"{mode}_reg_context_save_region_end:\n\n")

    def generate_cstructs_defines(self, file_descriptor):
        """Generate #define statements for struct sizes and field counts."""
        for c_struct in self.c_structs:
            # Generate defines for array field counts
            for field in c_struct.fields:
                if field.num_elements > 1:
                    file_descriptor.write(
                        f"#define NUM_{field.name.upper()} {field.num_elements}\n"
                    )

            # Generate struct size define
            file_descriptor.write(
                f"#define {c_struct.name.upper()}_STRUCT_SIZE_IN_BYTES {c_struct.size_in_bytes}\n\n"
            )

            # Generate field offset defines and getter/setter macros for thread_attributes
            if c_struct.name == "thread_attributes":
                for field in c_struct.fields:
                    file_descriptor.write(
                        f"#define {c_struct.name.upper()}_{field.name.upper()}_OFFSET {field.offset}\n"
                    )
                    file_descriptor.write(
                        f"#define GET_{c_struct.name.upper()}_{field.name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.LOAD, field.size_in_bytes)}   dest_reg, {c_struct.name.upper()}_{field.name.upper()}_OFFSET(tp);\n"
                    )
                    file_descriptor.write(
                        f"#define SET_{c_struct.name.upper()}_{field.name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.STORE, field.size_in_bytes)}   dest_reg, {c_struct.name.upper()}_{field.name.upper()}_OFFSET(tp);\n\n"
                    )

    def generate_cstructs_data_structures(self, file_descriptor):
        """Generate C struct definitions."""
        for c_struct in self.c_structs:
            file_descriptor.write(f"struct {c_struct.name} {{\n")
            for field in c_struct.fields:
                if field.num_elements > 1:
                    file_descriptor.write(
                        f"    {field.field_type} {field.name}[NUM_{field.name.upper()}];\n"
                    )
                else:
                    file_descriptor.write(f"    {field.field_type} {field.name};\n")
            file_descriptor.write(f"}} __attribute__((aligned({c_struct.alignment})));\n\n")

            # Generate offsetof assertions for compile-time verification
            self._generate_offsetof_assertions(c_struct, file_descriptor)

    def _generate_offsetof_assertions(self, c_struct, file_descriptor):
        """Generate _Static_assert statements using offsetof() for compile-time verification."""
        for field in c_struct.fields:
            file_descriptor.write(
                f"_Static_assert(offsetof(struct {c_struct.name}, {field.name}) == {field.offset}, "
                f'"{c_struct.name}.{field.name} offset mismatch");\n'
            )

        # Generate size assertion
        file_descriptor.write(
            f"_Static_assert(sizeof(struct {c_struct.name}) == {c_struct.name.upper()}_STRUCT_SIZE_IN_BYTES, "
            f'"{c_struct.name} size mismatch");\n\n'
        )

    def generate_cstructs_assembly(self, file_descriptor):
        """Generate assembly code for struct regions and getter/setter functions."""
        for c_struct in self.c_structs:
            # Generate assembly regions
            file_descriptor.write('.section .jumpstart.cpu.c_structs.mmode, "aw"\n\n')
            file_descriptor.write(f".global {c_struct.name}_region\n")
            file_descriptor.write(f"{c_struct.name}_region:\n")
            for i in range(self.max_num_cpus_supported):
                file_descriptor.write(f".global {c_struct.name}_region_cpu_{i}\n")
                file_descriptor.write(f"{c_struct.name}_region_cpu_{i}:\n")
                file_descriptor.write(f"  .zero {c_struct.size_in_bytes}\n")
            file_descriptor.write(f".global {c_struct.name}_region_end\n")
            file_descriptor.write(f"{c_struct.name}_region_end:\n\n")

            # Generate getter/setter functions for thread_attributes
            if c_struct.name == "thread_attributes":
                modes = ListUtils.intersection(["smode", "mmode"], self.priv_modes_enabled)
                for field in c_struct.fields:
                    for mode in modes:
                        file_descriptor.write(f'.section .jumpstart.cpu.text.{mode}, "ax"\n')
                        getter_method = f"get_{c_struct.name}_{field.name}_from_{mode}"
                        file_descriptor.write(f".global {getter_method}\n")
                        file_descriptor.write(f"{getter_method}:\n")
                        file_descriptor.write(
                            f"    GET_{c_struct.name.upper()}_{field.name.upper()}(a0)\n"
                        )
                        file_descriptor.write("    ret\n\n")

                        file_descriptor.write(
                            f".global set_{c_struct.name}_{field.name}_from_{mode}\n"
                        )
                        file_descriptor.write(f"set_{c_struct.name}_{field.name}_from_{mode}:\n")
                        file_descriptor.write(
                            f"    SET_{c_struct.name.upper()}_{field.name.upper()}(a0)\n"
                        )
                        file_descriptor.write("    ret\n\n")

        # Validate total size
        total_size_of_c_structs = sum(c_struct.size_in_bytes for c_struct in self.c_structs)

        # Find the MemoryMapping object for c_structs
        linker_section = ".jumpstart.cpu.c_structs.mmode"
        c_structs_mapping = self.find_memory_mapping_by_linker_section(linker_section, "cpu")
        if c_structs_mapping is None:
            raise Exception(
                f"MemoryMapping with linker_script_section '{linker_section}' not found in memory_map"
            )

        # Get the num_pages and page_size from the MemoryMapping object
        num_pages_for_c_structs = c_structs_mapping.get_field("num_pages")
        c_structs_page_size = c_structs_mapping.get_field("page_size")

        max_allowed_size_of_c_structs = num_pages_for_c_structs * c_structs_page_size

        if total_size_of_c_structs * self.max_num_cpus_supported > max_allowed_size_of_c_structs:
            raise Exception(
                f"Total size of C structs ({total_size_of_c_structs}) exceeds maximum size allocated for C structs {max_allowed_size_of_c_structs}"
            )

    def _parse_c_structs(self):
        """Parse C structs from YAML data into CStruct objects."""
        c_structs = []
        for struct_name, struct_data in self.jumpstart_source_attributes["c_structs"].items():
            c_struct = CStruct(struct_name, struct_data["fields"])
            c_structs.append(c_struct)
        return c_structs

    def translate(self, source_address):
        for target_mmu in MemoryMapping.get_supported_targets():
            for stage in TranslationStage.get_enabled_stages():
                try:
                    self.translate_stage(target_mmu, stage, source_address)
                    log.info(f"{target_mmu} MMU: {stage} Stage: Translation SUCCESS\n\n")
                except Exception as e:
                    log.warning(f"{target_mmu} MMU: {stage} Stage: Translation FAILED: {e}\n\n")

    def translate_stage(self, target_mmu, stage, source_address):
        translation_mode = TranslationStage.get_selected_mode_for_stage(stage)
        log.info(
            f"{target_mmu} MMU: {stage} Stage: Translating Address {hex(source_address)}. Translation.translation_mode = {translation_mode}."
        )

        attributes = PageTableAttributes(translation_mode)

        # Step 1
        a = self.page_tables[target_mmu][stage].get_start_address()

        current_level = 0
        pte_value = 0

        # Step 2
        while True:
            log.info(
                f"    {target_mmu} MMU: {stage} Stage: a = {hex(a)}; current_level = {current_level}"
            )

            pte_address = a + BitField.extract_bits(
                source_address, attributes.get_attribute("va_vpn_bits")[current_level]
            ) * attributes.get_attribute("pte_size_in_bytes")

            if TranslationStage.get_next_stage(stage) is not None:
                log.info(
                    f"    {target_mmu} MMU: {stage} Stage: PTE Address {hex(pte_address)} needs next stage translation."
                )
                self.translate_stage(
                    target_mmu, TranslationStage.get_next_stage(stage), pte_address
                )

            pte_value = self.page_tables[target_mmu][stage].read_sparse_memory(pte_address)

            if pte_value is None:
                raise ValueError(f"Level {current_level} PTE at {hex(pte_address)} is not valid.")

            log.info(
                f"    {target_mmu} MMU: {stage} Stage: level{current_level} PTE: [{hex(pte_address)}] = {hex(pte_value)}"
            )

            if BitField.extract_bits(pte_value, attributes.common_attributes["valid_bit"]) == 0:
                raise Exception(f"PTE at {hex(pte_address)} is not valid")

            xwr = BitField.extract_bits(pte_value, attributes.common_attributes["xwr_bits"])
            if (xwr & 0x3) == 0x2:
                raise Exception(f"PTE at {hex(pte_address)} has R=0 and X=1")

            a = 0
            for ppn_id in range(len(attributes.get_attribute("pte_ppn_bits"))):
                ppn_value = BitField.extract_bits(
                    pte_value, attributes.get_attribute("pte_ppn_bits")[ppn_id]
                )
                a = BitField.place_bits(
                    a, ppn_value, attributes.get_attribute("pa_ppn_bits")[ppn_id]
                )

            if (xwr & 0x6) or (xwr & 0x1):
                log.info(f"    {target_mmu} MMU: {stage} Stage: This is a Leaf PTE")
                break
            else:
                if BitField.extract_bits(pte_value, attributes.common_attributes["a_bit"]) != 0:
                    log.error("PTE has A=1 but is not a Leaf PTE")
                    sys.exit(1)
                elif BitField.extract_bits(pte_value, attributes.common_attributes["d_bit"]) != 0:
                    raise Exception("PTE has D=1 but is not a Leaf PTE")

            current_level += 1
            assert current_level < attributes.get_attribute("num_levels")
            continue

        dest_address = a
        dest_address += BitField.extract_bits(
            source_address, (attributes.get_attribute("va_vpn_bits")[current_level][1] - 1, 0)
        )

        log.info(f"    {target_mmu} MMU: {stage} Stage: PTE value = {hex(pte_value)}")
        log.info(
            f"{target_mmu} MMU: {stage} Stage: Translated {hex(source_address)} --> {hex(dest_address)}"
        )

        return dest_address


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diag_attributes_yaml", help="Diag Attributes YAML file", required=True, type=str
    )
    parser.add_argument(
        "--override_diag_attributes",
        help="Overrides the specified diag attributes.",
        required=False,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--jumpstart_source_attributes_yaml",
        help="YAML containing the jumpstart attributes.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--priv_modes_enabled",
        help=".",
        required=True,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--output_assembly_file",
        help="Assembly file to generate with page table mappings",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--output_defines_file",
        help="Defines file to hold the diag defines.",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--output_linker_script", help="Linker script to generate", required=False, type=str
    )
    parser.add_argument(
        "--output_data_structures_file",
        help="Data structures file to generate with C struct definitions",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--translate",
        help="Translate the address.",
        required=False,
        type=lambda x: int(x, 0),
    )
    parser.add_argument(
        "-v", "--verbose", help="Verbose output.", action="store_true", default=False
    )
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.DEBUG)
    else:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.INFO)

    if os.path.exists(args.diag_attributes_yaml) is False:
        raise Exception(f"Diag Attributes file {args.diag_attributes_yaml} not found")

    if os.path.exists(args.jumpstart_source_attributes_yaml) is False:
        raise Exception(
            f"JumpStart Attributes file {args.jumpstart_source_attributes_yaml} not found"
        )

    source_generator = SourceGenerator(
        args.jumpstart_source_attributes_yaml,
        args.diag_attributes_yaml,
        args.override_diag_attributes,
        args.priv_modes_enabled,
    )

    if args.output_linker_script is not None:
        source_generator.generate_linker_script(args.output_linker_script)
    if args.output_assembly_file is not None:
        source_generator.generate_assembly_file(args.output_assembly_file)
    if args.output_defines_file is not None:
        source_generator.generate_defines_file(args.output_defines_file)
    if args.output_data_structures_file is not None:
        source_generator.generate_data_structures_file(args.output_data_structures_file)

    if args.translate is not None:
        source_generator.translate(args.translate)


if __name__ == "__main__":
    main()
