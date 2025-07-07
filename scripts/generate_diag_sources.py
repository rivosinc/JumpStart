#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the diag source files based on the diag attributes file.

import argparse
import logging as log
import math
import os
import sys

import public.functions as public_functions
import yaml
from data_structures import BitField, DictUtils, ListUtils
from memory_management import (
    LinkerScript,
    MemoryMapping,
    PageSize,
    PageTableAttributes,
    PageTables,
    TranslationMode,
    TranslationStage,
)

try:
    import rivos_internal.functions as rivos_internal_functions
except ImportError:
    log.debug("rivos_internal Python module not present.")


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

        self.create_page_tables_data()

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
            # Warn if the command line overrides override existing keys.
            for key in cmd_line_diag_attribute_override_dict:
                if key in self.jumpstart_source_attributes["diag_attributes"]:
                    log.warning(
                        f"Command line overrides diag attribute {key}. {self.jumpstart_source_attributes['diag_attributes'][key]} -> {cmd_line_diag_attribute_override_dict[key]}"
                    )
            DictUtils.override_dict(
                self.jumpstart_source_attributes["diag_attributes"],
                cmd_line_diag_attribute_override_dict,
            )

        TranslationStage.set_virtualization_enabled(
            self.jumpstart_source_attributes["diag_attributes"]["enable_virtualization"]
        )

        self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"] = int(
            self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"], 2
        )

        if self.jumpstart_source_attributes["diag_attributes"]["primary_hart_id"] is None:
            active_hart_mask = self.jumpstart_source_attributes["diag_attributes"][
                "active_hart_mask"
            ]
            # Set the lowest index of the lowest bit set in active_hart_mask as the primary hart id.
            self.jumpstart_source_attributes["diag_attributes"]["primary_hart_id"] = (
                active_hart_mask & -active_hart_mask
            ).bit_length() - 1

        self.sanity_check_diag_attributes()

        for stage in TranslationStage.get_enabled_stages():
            TranslationStage.set_selected_mode_for_stage(
                stage,
                self.jumpstart_source_attributes["diag_attributes"][
                    f"{TranslationStage.get_atp_register(stage)}_mode"
                ],
            )

    def process_memory_map(self):
        self.memory_map = {stage: [] for stage in TranslationStage.get_enabled_stages()}

        for mapping in self.jumpstart_source_attributes["diag_attributes"]["mappings"]:
            mapping = MemoryMapping(mapping)
            self.memory_map[mapping.get_field("translation_stage")].append(mapping)

        self.add_jumpstart_sections_to_mappings()

        for stage in self.memory_map.keys():
            # Sort all the mappings by the destination address.
            self.memory_map[stage] = sorted(
                self.memory_map[stage],
                key=lambda x: x.get_field(TranslationStage.get_translates_to(stage)),
                reverse=False,
            )

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal_functions.process_memory_map(self.memory_map)

        self.sanity_check_memory_map()

    def create_page_tables_data(self):
        self.page_tables = {}
        for stage in TranslationStage.get_enabled_stages():
            translation_mode = TranslationStage.get_selected_mode_for_stage(stage)
            if translation_mode == "bare":
                # No pagetable mappings for the bare mode.
                continue

            self.page_tables[stage] = PageTables(
                translation_mode,
                self.jumpstart_source_attributes["diag_attributes"][
                    "max_num_pagetable_pages_per_stage"
                ],
                self.memory_map[stage],
            )

    def sanity_check_memory_map(self):
        public_functions.sanity_check_memory_map(self.memory_map)

        if self.jumpstart_source_attributes["rivos_internal_build"] is True:
            rivos_internal_functions.sanity_check_memory_map(self.memory_map)

    def add_pagetable_mappings(self, start_address):
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
            section_mapping["linker_script_section"] = f".jumpstart.rodata.{stage}_stage.pagetables"

            per_stage_pagetable_mappings[stage] = MemoryMapping(section_mapping)

            self.memory_map[stage].insert(
                len(self.memory_map[stage]), per_stage_pagetable_mappings[stage]
            )

            start_address += common_attributes["num_pages"] * common_attributes["page_size"]

        if "g" in TranslationStage.get_enabled_stages():
            vs_stage_memory_mapping = per_stage_pagetable_mappings["vs"].copy()

            vs_stage_memory_mapping.set_field("translation_stage", "g")

            start_address = vs_stage_memory_mapping.get_field(
                TranslationStage.get_translates_to("vs")
            )
            vs_stage_memory_mapping.set_field(TranslationStage.get_translates_from("vs"), None)
            vs_stage_memory_mapping.set_field(TranslationStage.get_translates_to("vs"), None)
            vs_stage_memory_mapping.set_field(
                TranslationStage.get_translates_from("g"), start_address
            )
            vs_stage_memory_mapping.set_field(
                TranslationStage.get_translates_to("g"), start_address
            )

            vs_stage_memory_mapping.set_field("umode", 1)

            self.memory_map["g"].insert(len(self.memory_map["g"]), vs_stage_memory_mapping)

        for stage in TranslationStage.get_enabled_stages():
            self.add_pa_guard_page_after_last_mapping(stage)

    def add_jumpstart_sections_to_mappings(self):
        pagetables_start_address = 0
        for stage in TranslationStage.get_enabled_stages():
            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                self.memory_map[stage].extend(
                    rivos_internal_functions.get_additional_mappings(
                        stage,
                        self.jumpstart_source_attributes,
                    )
                )

            for mode in self.priv_modes_enabled:
                self.add_jumpstart_mode_mappings_for_stage(stage, mode)

            # Pagetables for each stage are placed consecutively in the physical address
            # space. We will place the pagetables after the last physical address
            # used by the jumpstart mappings in any stage.
            # Note: get_next_available_dest_addr_after_last_mapping expects target_mmu but
            # current memory_map structure is {stage: []}, so we use stage directly
            if len(self.memory_map[stage]) > 0:
                previous_mapping_id = len(self.memory_map[stage]) - 1
                previous_mapping = self.memory_map[stage][previous_mapping_id]
                previous_mapping_size = previous_mapping.get_field(
                    "page_size"
                ) * previous_mapping.get_field("num_pages")
                dest_address_type = TranslationStage.get_translates_to(stage)
                next_available_dest_address = (
                    previous_mapping.get_field(dest_address_type) + previous_mapping_size
                )
            else:
                next_available_dest_address = 0
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
            self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"].bit_count()
            <= self.jumpstart_source_attributes["max_num_harts_supported"]
        )
        primary_hart_id = int(
            self.jumpstart_source_attributes["diag_attributes"]["primary_hart_id"]
        )
        assert (
            self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"]
            & (1 << primary_hart_id)
        ) != 0

    def get_next_available_dest_addr_after_last_mapping(
        self, target_mmu, stage, page_size, pma_memory_type
    ):
        # Handle both memory_map structures: {stage: []} and {target_mmu: {stage: []}}
        if target_mmu in self.memory_map and isinstance(self.memory_map[target_mmu], dict):
            # New structure: {target_mmu: {stage: []}}
            assert len(self.memory_map[target_mmu][stage]) > 0, "No previous mappings found."
            previous_mapping_id = len(self.memory_map[target_mmu][stage]) - 1
            previous_mapping = self.memory_map[target_mmu][stage][previous_mapping_id]
        else:
            # Old structure: {stage: []}
            assert len(self.memory_map[stage]) > 0, "No previous mappings found."
            previous_mapping_id = len(self.memory_map[stage]) - 1
            previous_mapping = self.memory_map[stage][previous_mapping_id]

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

    def add_jumpstart_mode_mappings_for_stage(self, stage, mode):
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
            section_mapping["translation_stage"] = stage

            if TranslationStage.get_selected_mode_for_stage(stage) == "bare":
                section_mapping["no_pte_allocation"] = True
                section_mapping.pop("xwr", None)
                section_mapping.pop("umode", None)

            for attribute in ["num_pages", "page_size"]:
                # This is where we allow the diag to override the attributes of jumpstart sections.
                # We can change the page size and num_pages of the section.
                #   Example: num_pages_for_jumpstart_smode_bss, num_pages_for_jumpstart_mmode_rodata, etc.
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
                # # of the last mapping.
                section_mapping[dest_address_type] = (
                    self.get_next_available_dest_addr_after_last_mapping(
                        "cpu",
                        stage,
                        section_mapping["page_size"],
                        section_mapping["pma_memory_type"],
                    )
                )

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

            self.memory_map[stage].insert(
                len(self.memory_map[stage]), MemoryMapping(section_mapping)
            )

    def add_pa_guard_page_after_last_mapping(self, stage):
        guard_page_mapping = {}
        guard_page_mapping["page_size"] = PageSize.SIZE_4K
        guard_page_mapping["pma_memory_type"] = "wb"
        guard_page_mapping["translation_stage"] = stage

        # Guard pages have no allocations in the page tables
        # but occupy space in the memory map.
        # They also don't occupy space in the ELFs.
        guard_page_mapping["no_pte_allocation"] = True
        guard_page_mapping["valid"] = "0b0"
        dest_address_type = TranslationStage.get_translates_to(stage)
        guard_page_mapping[dest_address_type] = (
            self.get_next_available_dest_addr_after_last_mapping(
                "cpu", stage, guard_page_mapping["page_size"], guard_page_mapping["pma_memory_type"]
            )
        )
        guard_page_mapping["num_pages"] = 1

        self.memory_map[stage].insert(
            len(self.memory_map[stage]), MemoryMapping(guard_page_mapping)
        )

    def generate_linker_script(self, output_linker_script):
        self.linker_script = LinkerScript(
            entry_label=self.jumpstart_source_attributes["diag_attributes"]["diag_entry_label"],
            elf_address_range=(
                self.jumpstart_source_attributes["diag_attributes"]["elf_start_address"],
                self.jumpstart_source_attributes["diag_attributes"]["elf_end_address"],
            ),
            mappings=self.memory_map,
            attributes_file=self.diag_attributes_yaml,
        )
        self.linker_script.generate(output_linker_script)

    def generate_defines_file(self, output_defines_file):
        with open(output_defines_file, "w") as file_descriptor:
            file_descriptor.write(
                f"// This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

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

            file_descriptor.close()

    def generate_hart_sync_functions(self, file_descriptor):
        active_hart_mask = self.jumpstart_source_attributes["diag_attributes"]["active_hart_mask"]
        primary_hart_id = self.jumpstart_source_attributes["diag_attributes"]["primary_hart_id"]

        modes = ListUtils.intersection(["mmode", "smode"], self.priv_modes_enabled)
        for mode in modes:
            file_descriptor.write(
                f"""
.section .jumpstart.cpu.text.{mode}, "ax"
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
  # twiddle thumbs to avoid excessive spinning
  pause
  lw t0, (a3)
  bne t0, a1, wait_for_all_harts_to_set_sync_point_bits_{mode}

  amoswap.w t0, zero, (a3)

  bne t0, a1, jumpstart_{mode}_fail

  j return_from_sync_harts_in_mask_from_{mode}

wait_for_primary_hart_to_clear_sync_point_bits_{mode}:
  # non-primary harts wait for the primary hart to clear the sync point bits.
  # twiddle thumbs to avoid excessive spinning
  pause
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
  li a2, {primary_hart_id}
  la a3, hart_sync_point

  jal sync_harts_in_mask_from_{mode}

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
                if stage in self.page_tables:
                    file_descriptor.write(f"    la t1, {self.page_tables[stage].get_asm_label()}\n")
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
        for stage in TranslationStage.get_enabled_stages():
            if stage not in self.page_tables:
                continue

            file_descriptor.write(f'.section .jumpstart.rodata.{stage}_stage.pagetables, "a"\n\n')

            file_descriptor.write(f".global {self.page_tables[stage].get_asm_label()}\n")
            file_descriptor.write(f"{self.page_tables[stage].get_asm_label()}:\n\n")

            file_descriptor.write("/* Memory mappings in this page table:\n")
            for mapping in self.page_tables[stage].get_mappings():
                if not mapping.is_bare_mapping():
                    file_descriptor.write(f"{mapping}\n")
            file_descriptor.write("*/\n")

            pte_size_in_bytes = self.page_tables[stage].get_attribute("pte_size_in_bytes")
            last_filled_address = None
            for address in list(sorted(self.page_tables[stage].get_pte_addresses())):
                if last_filled_address is not None and address != (
                    last_filled_address + pte_size_in_bytes
                ):
                    file_descriptor.write(
                        f".skip {hex(address - (last_filled_address + pte_size_in_bytes))}\n"
                    )
                log.debug(
                    f"Writing [{hex(address)}] = {hex(self.page_tables[stage].get_pte(address))}"
                )
                file_descriptor.write(f"\n# [{hex(address)}]\n")
                file_descriptor.write(
                    f".{pte_size_in_bytes}byte {hex(self.page_tables[stage].get_pte(address))}\n"
                )

                last_filled_address = address

    def generate_linker_guard_sections(self, file_descriptor):
        assert self.linker_script.get_guard_sections() is not None
        for guard_section in self.linker_script.get_guard_sections():
            file_descriptor.write(f'\n\n.section {guard_section.get_top_level_name()}, "a"\n\n')
            file_descriptor.write(f"dummy_data_for_{guard_section.get_top_level_name()}:\n")
            file_descriptor.write(
                f".fill {int(guard_section.get_size() / 8)}, 8, 0xF00D44C0DE44F00D\n\n"
            )

    def generate_assembly_file(self, output_assembly_file):
        with open(output_assembly_file, "w") as file:
            file.write(
                f"# This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

            file.write('#include "jumpstart_defines.h"\n\n')
            file.write('#include "cpu_bits.h"\n\n')

            self.generate_mmu_functions(file)

            self.generate_smode_fail_functions(file)

            self.generate_hart_sync_functions(file)

            if self.jumpstart_source_attributes["rivos_internal_build"] is True:
                rivos_internal_functions.generate_rivos_internal_mmu_functions(
                    file, self.priv_modes_enabled
                )

            self.generate_page_tables(file)

            self.generate_linker_guard_sections(file)

            file.close()

    def translate(self, source_address):
        for stage in TranslationStage.get_enabled_stages():
            try:
                self.translate_stage(stage, source_address)
                log.info(f"{stage} Stage: Translation SUCCESS\n\n")
            except Exception as e:
                log.warning(f"{stage} Stage: Translation FAILED: {e}\n\n")

    def translate_stage(self, stage, source_address):
        translation_mode = TranslationStage.get_selected_mode_for_stage(stage)
        log.info(
            f"{stage} Stage: Translating Address {hex(source_address)}. Translation.translation_mode = {translation_mode}."
        )

        attributes = PageTableAttributes(translation_mode)

        # Step 1
        a = self.page_tables[stage].get_start_address()

        current_level = 0
        pte_value = 0

        # Step 2
        while True:
            log.info(f"    {stage} Stage: a = {hex(a)}; current_level = {current_level}")

            pte_address = a + BitField.extract_bits(
                source_address, attributes.get_attribute("va_vpn_bits")[current_level]
            ) * attributes.get_attribute("pte_size_in_bytes")

            if TranslationStage.get_next_stage(stage) is not None:
                log.info(
                    f"    {stage} Stage: PTE Address {hex(pte_address)} needs next stage translation."
                )
                self.translate_stage(TranslationStage.get_next_stage(stage), pte_address)

            pte_value = self.page_tables[stage].read_sparse_memory(pte_address)

            if pte_value is None:
                raise ValueError(f"Level {current_level} PTE at {hex(pte_address)} is not valid.")

            log.info(
                f"    {stage} Stage: level{current_level} PTE: [{hex(pte_address)}] = {hex(pte_value)}"
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
                log.info(f"    {stage} Stage: This is a Leaf PTE")
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

        log.info(f"    {stage} Stage: PTE value = {hex(pte_value)}")
        log.info(f"{stage} Stage: Translated {hex(source_address)} --> {hex(dest_address)}")

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

    if args.translate is not None:
        source_generator.translate(args.translate)


if __name__ == "__main__":
    main()
