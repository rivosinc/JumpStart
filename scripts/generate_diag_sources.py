#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the diag source files based on the diag attributes file.

import argparse
import logging as log
import math
import os
import sys

import public.lib as public
import yaml
from memory_mapping.lib import MemoryMapping, PageSize
from pagetables.lib import PageTableAttributes, PageTables
from utils.lib import DictUtils, ListUtils

try:
    import rivos_internal.lib as rivos_internal
except ImportError:
    log.debug("rivos_internal Python module not present.")


class BooleanDiagAttribute:
    def __init__(self, attribute, modes):
        self.name = attribute
        self.modes = modes

    def get_name(self):
        return self.name

    def get_modes(self):
        return self.modes


class DiagSource:
    def __init__(
        self,
        jumpstart_source_attributes_yaml,
        override_jumpstart_source_attributes,
        diag_attributes_yaml,
        override_diag_attributes,
        supported_modes,
    ):
        self.num_guard_pages_generated = 0

        self.diag_attributes_yaml = diag_attributes_yaml
        with open(diag_attributes_yaml) as f:
            diag_attributes = yaml.safe_load(f)

        with open(jumpstart_source_attributes_yaml) as f:
            self.jumpstart_source_attributes = yaml.safe_load(f)

        self.supported_modes = supported_modes

        rivos_internal_lib_dir = f"{os.path.dirname(os.path.realpath(__file__))}/rivos_internal"

        if (
            self.jumpstart_source_attributes["rivos_internal_build"] is True
            and os.path.isdir(rivos_internal_lib_dir) is False
        ):
            log.error(
                f"rivos_internal.lib not found but rivos_internal_build is set to True in {jumpstart_source_attributes_yaml}"
            )
            sys.exit(1)
        elif (
            self.jumpstart_source_attributes["rivos_internal_build"] is False
            and os.path.isdir(rivos_internal_lib_dir) is True
        ):
            log.warning(
                f"rivos_internal.lib exists but rivos_internal_build is set to False in {jumpstart_source_attributes_yaml}"
            )

        if override_jumpstart_source_attributes:
            # Override the default jumpstart source attribute values with the values
            # specified on the command line.
            DictUtils.override_dict(
                self.jumpstart_source_attributes,
                DictUtils.create_dict(override_jumpstart_source_attributes),
            )

        # Override the default diag attribute values with the values
        # specified by the diag.
        DictUtils.override_dict(
            self.jumpstart_source_attributes["diag_attributes"], diag_attributes
        )

        if override_diag_attributes is not None:
            # Override the diag attributes with the values specified on the
            # command line.
            DictUtils.override_dict(
                self.jumpstart_source_attributes["diag_attributes"],
                DictUtils.create_dict(override_diag_attributes),
            )

        self.sanity_check_diag_attributes()

        self.memory_map = []
        for mapping in self.jumpstart_source_attributes["diag_attributes"]["mappings"]:
            self.memory_map.append(MemoryMapping(mapping))

        self.add_jumpstart_sections_to_mappings()

        # Sort all the mappings by the PA.
        self.memory_map = sorted(
            self.memory_map,
            key=lambda x: x.get_field("pa"),
            reverse=False,
        )

        self.sanity_check_memory_map()

        self.page_tables = PageTables(
            self.jumpstart_source_attributes["diag_attributes"]["satp_mode"],
            self.jumpstart_source_attributes["diag_attributes"][
                "num_pages_for_jumpstart_smode_pagetables"
            ],
            self.memory_map,
        )

    def sanity_check_memory_map(self):
        public.sanity_check_memory_map(self.memory_map)

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal.sanity_check_memory_map(self.memory_map)

    def add_jumpstart_sections_to_mappings(self):
        # The rivos internal sections are added at specific locations.
        # The sections for the other jumpstart areas can be addded at
        # specific locations or at locations immediately following the
        # previous section using the *_start_address diag_attributes attribute.
        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            self.memory_map.extend(
                rivos_internal.get_rivos_specific_mappings(
                    self.jumpstart_source_attributes,
                )
            )

        for mode in ListUtils.intersection(["mmode", "smode", "umode"], self.supported_modes):
            self.add_mappings_for_jumpstart_mode(mode)

        self.add_pa_guard_page_after_last_mapping()

    def sanity_check_diag_attributes(self):
        assert "satp_mode" in self.jumpstart_source_attributes["diag_attributes"]
        assert (
            self.jumpstart_source_attributes["diag_attributes"]["satp_mode"]
            in PageTableAttributes.mode_attributes
        )

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal.sanity_check_diag_attributes(
                self.jumpstart_source_attributes["diag_attributes"]
            )

    def get_next_available_pa_after_last_mapping(self, page_size, pma_memory_type):
        previous_mapping_id = len(self.memory_map) - 1
        previous_mapping = self.memory_map[previous_mapping_id]

        previous_mapping_size = previous_mapping.get_field(
            "page_size"
        ) * previous_mapping.get_field("num_pages")
        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            previous_mapping_size = rivos_internal.get_previous_mapping_size(
                previous_mapping, pma_memory_type
            )

        next_available_pa = previous_mapping.get_field("pa") + previous_mapping_size

        if (next_available_pa % page_size) != 0:
            # Align the PA to the page size.
            next_available_pa = (math.floor(next_available_pa / page_size) + 1) * page_size

        return next_available_pa

    def add_mappings_for_jumpstart_mode(self, mode):
        area_name = f"jumpstart_{mode}"

        # We pick up the start PA of the area from the diag_attributes
        #   Example: mmode_start_address, smode_start_address,
        #            umode_start_address
        # If this attribute is not null we use it to set up the address of the
        # first section in the area. Every subsequent section will just follow
        # the previous section in the PA space.
        area_start_pa = None
        area_start_address_attribute_name = f"{mode}_start_address"
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
            section_mapping = self.jumpstart_source_attributes[area_name][section_name]

            assert "pa" not in section_mapping
            if area_start_pa is not None:
                section_mapping["pa"] = area_start_pa
                # Every subsequent section will just follow the previous section
                # in the PA space.
                area_start_pa = None
            else:
                # We're going to start the PA of the new mapping after the PA range
                # # of the last mapping.
                section_mapping["pa"] = self.get_next_available_pa_after_last_mapping(
                    self.jumpstart_source_attributes[area_name][section_name]["page_size"],
                    self.jumpstart_source_attributes[area_name][section_name]["pma_memory_type"],
                )

            if (
                "no_pte_allocation" not in section_mapping
                or section_mapping["no_pte_allocation"] is False
            ):
                section_mapping["va"] = section_mapping["pa"]

            # This is where we pick up num_pages_for_jumpstart_*mode_* attributes from the diag_attributes
            #   Example: num_pages_for_jumpstart_smode_pagetables, num_pages_for_jumpstart_smode_bss,
            #            num_pages_for_jumpstart_smode_rodata, etc.
            num_pages_diag_attribute_name = f"num_pages_for_{area_name}_{section_name}"
            if (
                "num_pages" in section_mapping
                and num_pages_diag_attribute_name
                in self.jumpstart_source_attributes["diag_attributes"]
            ):
                raise Exception(
                    f"num_pages specified for {section_name} in {area_name} and {num_pages_diag_attribute_name} specified in diag_attributes."
                )

            if num_pages_diag_attribute_name in self.jumpstart_source_attributes["diag_attributes"]:
                section_mapping["num_pages"] = self.jumpstart_source_attributes["diag_attributes"][
                    num_pages_diag_attribute_name
                ]

            if (
                section_name == "pagetables"
                and self.jumpstart_source_attributes["diag_attributes"][
                    "allow_page_table_modifications"
                ]
                is True
            ):
                section_mapping["xwr"] = "0b011"

            self.memory_map.insert(len(self.memory_map), MemoryMapping(section_mapping))

    def add_pa_guard_page_after_last_mapping(self):
        guard_page_mapping = {}
        guard_page_mapping["page_size"] = PageSize.SIZE_4K
        guard_page_mapping["pma_memory_type"] = "wb"
        guard_page_mapping["pa"] = self.get_next_available_pa_after_last_mapping(
            guard_page_mapping["page_size"], guard_page_mapping["pma_memory_type"]
        )
        guard_page_mapping["num_pages"] = 1
        guard_page_mapping[
            "linker_script_section"
        ] = f".jumpstart.guard_page.{self.num_guard_pages_generated}"
        # Guard pages have no allocations in the page tables but occupy space in the memory map.
        guard_page_mapping["no_pte_allocation"] = True

        self.memory_map.insert(len(self.memory_map), MemoryMapping(guard_page_mapping))

        self.num_guard_pages_generated += 1

    def generate_linker_script(self, output_linker_script):
        with open(output_linker_script, "w") as file:
            file.write(
                f"/* This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml} */\n"
            )
            file.write(
                f"/* SATP.Mode is {self.jumpstart_source_attributes['diag_attributes']['satp_mode']} */\n\n"
            )
            file.write('OUTPUT_ARCH( "riscv" )\n')
            file.write(f"ENTRY({self.jumpstart_source_attributes['diag_entry_label']})\n\n")

            file.write("SECTIONS\n{\n")
            defined_sections = []

            # The linker script lays out the diag in physical memory. The
            # mappings are already sorted by PA.
            for entry in self.memory_map:
                if entry.get_field("linker_script_section") is None:
                    # We don't generate linker script sections for entries
                    # that don't have a linker_script_section attribute.
                    continue

                file.write(f"   /* {entry.get_field('linker_script_section')}:\n")
                file.write(
                    f"       PA Range: {hex(entry.get_field('pa'))} - {hex(entry.get_field('pa') + entry.get_field('num_pages') * entry.get_field('page_size'))}\n"
                )
                file.write("   */\n")
                file.write(f"   . = {hex(entry.get_field('pa'))};\n")

                # If this is a list of sections, the first section listed is the
                # top level section that all the other sections get placed in.
                linker_script_sections = entry.get_field("linker_script_section").split(",")

                top_level_section_name = linker_script_sections[0]

                # main() automatically gets placed in the .text.startup section
                # and we want the .text.startup section to be part of the
                # .text section.
                if (
                    ".text" in linker_script_sections
                    and ".text.startup" not in linker_script_sections
                ):
                    # Place .text.startup at the beginning of the list
                    # so that main() is the first thing in the .text section?
                    linker_script_sections.insert(0, ".text.startup")

                file.write(f"   {top_level_section_name} : {{\n")
                top_level_section_variable_name_prefix = top_level_section_name.replace(
                    ".", "_"
                ).upper()
                file.write(f"   {top_level_section_variable_name_prefix}_START = .;\n")
                for section_name in linker_script_sections:
                    assert section_name not in defined_sections
                    file.write(f"      *({section_name})\n")
                    defined_sections.append(section_name)
                file.write("   }\n\n")
                file.write(
                    f"   . = {hex(entry.get_field('pa') + entry.get_field('num_pages') * entry.get_field('page_size') - 1)};\n"
                )
                file.write(f"  {top_level_section_variable_name_prefix}_END = .;\n")
            file.write("\n}\n")

            file.close()

    def generate_diag_attribute_functions(self, file_descriptor):
        boolean_attributes = [BooleanDiagAttribute("start_test_in_mmode", ["mmode"])]

        self.generate_get_active_hart_mask_function(file_descriptor)
        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal.generate_rivos_internal_diag_attribute_functions(
                file_descriptor,
                self.jumpstart_source_attributes["diag_attributes"],
                self.supported_modes,
            )

            rivos_internal_boolean_attributes = rivos_internal.get_boolean_diag_attributes()

            for rivos_internal_attribute in rivos_internal_boolean_attributes:
                boolean_attributes.append(
                    BooleanDiagAttribute(rivos_internal_attribute[0], rivos_internal_attribute[1])
                )

        self.generate_boolean_diag_attribute_functions(file_descriptor, boolean_attributes)

    def generate_boolean_diag_attribute_functions(self, file_descriptor, boolean_attributes):
        for attribute in boolean_attributes:
            modes = ListUtils.intersection(attribute.get_modes(), self.supported_modes)
            for mode in modes:
                file_descriptor.write(f'.section .jumpstart.text.{mode}, "ax"\n\n')
                attribute_function_name = f"{attribute.get_name()}"
                file_descriptor.write(f".global {attribute_function_name}_from_{mode}\n")
                file_descriptor.write(f"{attribute_function_name}_from_{mode}:\n\n")
                if len(modes) == 1:
                    file_descriptor.write(f".global {attribute_function_name}\n")
                    file_descriptor.write(f"{attribute_function_name}:\n\n")

                attribute_value = int(
                    self.jumpstart_source_attributes["diag_attributes"][attribute.get_name()]
                )

                file_descriptor.write(f"   li a0, {attribute_value}\n")
                file_descriptor.write("   ret\n\n\n")

    def generate_get_active_hart_mask_function(self, file_descriptor):
        modes = ListUtils.intersection(["mmode", "smode"], self.supported_modes)
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.text.{mode}, "ax"\n\n')
            file_descriptor.write(f".global get_active_hart_mask_from_{mode}\n")
            file_descriptor.write(f"get_active_hart_mask_from_{mode}:\n\n")

            active_hart_mask = int(
                self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"], 2
            )

            assert (
                active_hart_mask.bit_count()
                <= self.jumpstart_source_attributes["max_num_harts_supported"]
            )

            file_descriptor.write(f"   li a0, {active_hart_mask}\n")
            file_descriptor.write("   ret\n\n\n")

    def generate_hart_sync_functions(self, file_descriptor):
        active_hart_mask = int(
            self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"], 2
        )

        modes = ListUtils.intersection(["mmode", "smode"], self.supported_modes)
        for mode in modes:
            file_descriptor.write(
                f"""
.section .jumpstart.text.{mode}, "ax"
# Inputs:
#   a0: hart id of current hart
#   a1: hart mask of harts to sync.
#   a2: hart id of primary hart for sync
#   a3: sync point address (4 byte aligned)
.global sync_harts_in_mask_from_{mode}
sync_harts_in_mask_from_{mode}:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  CHECKTC_DISABLE

  li t0, 1
  sll t2, t0, a0
  sll t0, t0, a2

  # Both this hart id and the primary hart id should be part of
  # the mask of harts to sync
  and t3, t2, a1
  beqz t3, jumpstart_{mode}_fail
  and t3, t0, a1
  beqz t3, jumpstart_{mode}_fail

  amoor.w.aqrl t3, t2, (a3)

  # This bit should not be already set.
  and t3, t3, t2
  bnez t3, jumpstart_{mode}_fail

  bne t0, t2, wait_for_primary_hart_to_clear_sync_point_bits_{mode}

wait_for_all_harts_to_set_sync_point_bits_{mode}:
  # Primary hart waits till all the harts have set their bits in the sync point.
  lw t0, (a3)
  bne t0, a1, wait_for_all_harts_to_set_sync_point_bits_{mode}

  amoswap.w t0, zero, (a3)

  bne t0, a1, jumpstart_{mode}_fail

  j return_from_sync_harts_in_mask_from_{mode}

wait_for_primary_hart_to_clear_sync_point_bits_{mode}:
  # non-primary harts wait for the primary hart to clear the sync point bits.
  lw t0, (a3)
  srl t0, t0, a0
  andi t0, t0, 1
  bnez t0, wait_for_primary_hart_to_clear_sync_point_bits_{mode}

return_from_sync_harts_in_mask_from_{mode}:
  CHECKTC_ENABLE

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret

.global sync_all_harts_from_{mode}
sync_all_harts_from_{mode}:
  addi  sp, sp, -16
  sd  ra, 8(sp)
  sd  fp, 0(sp)
  addi    fp, sp, 16

  jal get_thread_attributes_hart_id_from_{mode}
  li a1, {active_hart_mask}
  li a2, PRIMARY_HART_ID
  la a3, hart_sync_point

  jal sync_harts_in_mask_from_{mode}

  ld  ra, 8(sp)
  ld  fp, 0(sp)
  addi  sp, sp, 16
  ret
        """
            )

    def generate_mmu_functions(self, file_descriptor):
        file_descriptor.write(
            f"# SATP.Mode is {self.jumpstart_source_attributes['diag_attributes']['satp_mode']}\n\n"
        )
        file_descriptor.write(
            f"#define DIAG_SATP_MODE {self.page_tables.get_attribute('satp_mode')}\n"
        )

        modes = ListUtils.intersection(["mmode", "smode"], self.supported_modes)
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.text.{mode}, "ax"\n\n')

            file_descriptor.write(f".global get_diag_satp_mode_from_{mode}\n")
            file_descriptor.write(f"get_diag_satp_mode_from_{mode}:\n\n")
            file_descriptor.write("    li   a0, DIAG_SATP_MODE\n")
            file_descriptor.write("    ret\n\n\n")

            file_descriptor.write(f".global setup_mmu_from_{mode}\n")
            file_descriptor.write(f"setup_mmu_from_{mode}:\n\n")
            file_descriptor.write("    li   t0, DIAG_SATP_MODE\n")
            file_descriptor.write("    slli  t0, t0, SATP64_MODE_SHIFT\n")
            file_descriptor.write(f"    la t1, {self.page_tables.get_asm_label()}\n")
            file_descriptor.write("    srai t1, t1, PAGE_OFFSET\n")
            file_descriptor.write("    add  t1, t1, t0\n")
            file_descriptor.write("    csrw  satp, t1\n")
            file_descriptor.write("    sfence.vma\n")
            file_descriptor.write("    ret\n")

    def generate_page_table_data(self, file_descriptor):
        file_descriptor.write('.section .jumpstart.rodata.pagetables, "a"\n\n')
        file_descriptor.write(f".global {self.page_tables.get_asm_label()}\n")
        file_descriptor.write(f"{self.page_tables.get_asm_label()}:\n\n")

        pagetable_filled_memory_addresses = list(sorted(self.page_tables.get_pte_addresses()))

        pte_size_in_bytes = self.page_tables.get_attribute("pte_size_in_bytes")
        last_filled_address = None
        for address in pagetable_filled_memory_addresses:
            if last_filled_address is not None and address != (
                last_filled_address + pte_size_in_bytes
            ):
                file_descriptor.write(
                    f".skip {hex(address - (last_filled_address + pte_size_in_bytes))}\n"
                )
            log.debug(f"Writing [{hex(address)}] = {hex(self.page_tables.get_pte(address))}")
            file_descriptor.write(f"\n# [{hex(address)}]\n")
            file_descriptor.write(
                f".{pte_size_in_bytes}byte {hex(self.page_tables.get_pte(address))}\n"
            )

            last_filled_address = address

    def generate_guard_pages(self, file_descriptor):
        for guard_page_id in range(self.num_guard_pages_generated):
            # @nobits reference:
            #   section does not contain data (i.e., section only occupies space)
            # https://ftp.gnu.org/old-gnu/Manuals/gas-2.9.1/html_node/as_117.html?cmdf=.section+nobits
            file_descriptor.write(
                f'\n\n.section .jumpstart.guard_page.{guard_page_id}, "a",@nobits\n'
            )
            file_descriptor.write(f".global guard_page_{guard_page_id}\n")
            file_descriptor.write(f"guard_page_{guard_page_id}:\n")
            file_descriptor.write(f".zero {PageSize.SIZE_4K}\n\n")

    def generate_assembly_file(self, output_assembly_file):
        with open(output_assembly_file, "w") as file:
            file.write(
                f"# This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

            file.write('#include "jumpstart_defines.h"\n\n')
            file.write('#include "cpu_bits.h"\n\n')

            self.generate_diag_attribute_functions(file)

            self.generate_mmu_functions(file)

            self.generate_hart_sync_functions(file)

            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                rivos_internal.generate_rivos_internal_mmu_functions(
                    file, self.memory_map, self.supported_modes
                )

            self.generate_page_table_data(file)

            self.generate_guard_pages(file)

            file.close()


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
        "--override_jumpstart_source_attributes",
        help="Overrides the JumpStart source attributes.",
        required=False,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--supported_modes",
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
        "--output_linker_script", help="Linker script to generate", required=False, type=str
    )
    parser.add_argument(
        "--translate_VA",
        help="Translate the given VA to PA",
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

    diag_source = DiagSource(
        args.jumpstart_source_attributes_yaml,
        args.override_jumpstart_source_attributes,
        args.diag_attributes_yaml,
        args.override_diag_attributes,
        args.supported_modes,
    )

    if args.output_assembly_file is not None:
        diag_source.generate_assembly_file(args.output_assembly_file)
    if args.output_linker_script is not None:
        diag_source.generate_linker_script(args.output_linker_script)

    if args.translate_VA is not None:
        diag_source.page_tables.translate_VA(args.translate_VA)


if __name__ == "__main__":
    main()
