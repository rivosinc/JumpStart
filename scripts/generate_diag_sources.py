#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

# Generates the diag source files based on the diag attributes file.

import argparse
import enum
import logging as log
import os
import sys

import yaml


def extract_bits(value, bit_range):
    msb = bit_range[0]
    lsb = bit_range[1]
    return (value >> lsb) & ((1 << (msb - lsb + 1)) - 1)


def place_bits(value, bits, bit_range):
    msb = bit_range[0]
    lsb = bit_range[1]
    return (value & ~(((1 << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb)


class PageTablePage:

    def __init__(self, sparse_memory_address, va, level, size):
        self.sparse_memory_address = sparse_memory_address
        self.va = va
        self.level = level
        self.size = size

    def __str__(self):
        return f"PageTablePage: sparse_memory_address={hex(self.sparse_memory_address)}, va={hex(self.va)}, level={hex(self.level)}, size={hex(self.size)}"

    def get_sparse_memory_address(self):
        return self.sparse_memory_address

    def get_va(self):
        return self.va

    def get_level(self):
        return self.level

    def get_size(self):
        return self.size

    def contains(self, va, level):
        if level != self.level:
            return False
        if va >= self.va and va < (self.va + self.size):
            return True
        return False


class PbmtMode(enum.IntEnum):
    PMA = 0
    NC = 1
    IO = 2


class PageTableAttributes:
    pt_start_label = "pagetables_start"

    common_attributes = {
        "page_offset": 12,
        "valid_bit": (0, 0),
        "xwr_bits": (3, 1),
        "umode_bit": (4, 4),
        "global_bit": (5, 5),
        "a_bit": (6, 6),
        "d_bit": (7, 7),
        "pbmt_bits": (62, 61),
    }

    mode_attributes = {
        "sv39": {
            "satp_mode": 8,
            "pte_size_in_bytes": 8,
            "num_levels": 3,
            "va_vpn_bits": [(38, 30), (29, 21), (20, 12)],
            "pa_ppn_bits": [(55, 30), (29, 21), (20, 12)],
            "pte_ppn_bits": [(53, 28), (27, 19), (18, 10)],
        },
        "sv48": {
            "satp_mode": 9,
            "pte_size_in_bytes": 8,
            "num_levels": 4,
            "va_vpn_bits": [(47, 39), (38, 30), (29, 21), (20, 12)],
            "pa_ppn_bits": [(55, 39), (38, 30), (29, 21), (20, 12)],
            "pte_ppn_bits": [(53, 37), (36, 28), (27, 19), (18, 10)],
        }
    }

    def convert_pbmt_mode_string_to_mode(self, mode_string):
        if mode_string == "pma":
            return PbmtMode.PMA
        elif mode_string == "nc":
            return PbmtMode.NC
        elif mode_string == "io":
            return PbmtMode.IO
        else:
            log.error(f"Unknown pbmt mode {mode_string}")
            sys.exit(1)

    def convert_pbmt_mode_to_string(self, mode):
        if mode == PbmtMode.PMA:
            return "pma"
        elif mode == PbmtMode.NC:
            return "nc"
        elif mode == PbmtMode.IO:
            return "io"
        else:
            log.error(f"Unknown pbmt mode {mode}")
            sys.exit(1)


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
        self.start_address = (start_address >> self.pmarr_attributes.base_lsb
                              ) << self.pmarr_attributes.base_lsb

        self.end_address = self.start_address + self.pmarr_attributes.minimum_size
        if end_address > self.end_address:
            self.end_address = end_address

        self.memory_type = self.pmarr_attributes.convert_string_to_memory_type(
            memory_type_string)

    def __str__(self):
        return f"PmarrRegion: start_address={hex(self.start_address)}, end_address={hex(self.end_address)}, memory_type={self.pmarr_attributes.convert_memory_type_to_string(self.memory_type)}"

    def can_add_to_region(self, start_address, end_address,
                          memory_type_string):
        memory_type = self.pmarr_attributes.convert_string_to_memory_type(
            memory_type_string)

        if (self.start_address <= (end_address - 1)) and (
                start_address <=
            (self.end_address - 1)) and memory_type != self.memory_type:
            log.error(
                f"Region [{hex(start_address)}, {hex(end_address)}, {memory_type_string}] overlaps with an existing PMARR region [{hex(self.start_address)}, {hex(self.end_address)}] with different memory type {self.pmarr_attributes.convert_memory_type_to_string(self.memory_type)}"
            )
            sys.exit(1)

        if (self.start_address <= end_address) and (
                start_address <=
                self.end_address) and memory_type == self.memory_type:
            return True

        return False

    def add_to_region(self, start_address, end_address):
        assert ((self.start_address <= end_address)
                and (start_address <= self.end_address))

        if start_address < self.start_address:
            self.start_address = start_address

        if self.end_address < end_address:
            self.end_address = end_address

    def generate_pmarr_region_setup_code(self, file_descriptor, reg_id):
        file_descriptor.write(f"   # {reg_id}: {self}\n")

        pmarr_base_reg_value = int(self.memory_type) | self.start_address

        region_size = self.end_address - self.start_address
        # Assuming that the region size is a multiple of the minimum size
        assert (region_size % self.pmarr_attributes.minimum_size == 0)
        pmarr_mask = (0xffffffffffffffff <<
                      (region_size.bit_length() - 1)) & 0xffffffffffffffff
        pmarr_mask_reg_value = pmarr_mask | 0x3  # set the L and V bits.

        file_descriptor.write(f"   li   t0, {hex(pmarr_base_reg_value)}\n")
        file_descriptor.write(f"   csrw pmarr_base_{reg_id}, t0\n")
        file_descriptor.write(f"   li   t0, {hex(pmarr_mask_reg_value)}\n")
        file_descriptor.write(f"   csrw pmarr_mask_{reg_id}, t0\n\n")


class DiagAttributes:
    pt_attributes = PageTableAttributes()
    num_guard_pages_generated = 0

    def __init__(self, jumpstart_source_attributes_yaml, diag_attributes_yaml,
                 override_diag_attributes):
        self.diag_attributes_yaml = diag_attributes_yaml

        with open(diag_attributes_yaml, "r") as f:
            diag_attributes = yaml.safe_load(f)

        with open(jumpstart_source_attributes_yaml, "r") as f:
            self.jumpstart_source_attributes = yaml.safe_load(f)

        # Override the default diag attribute values with the values
        # specified by the diag.
        for key in diag_attributes.keys():
            if key not in self.jumpstart_source_attributes['diag_attributes']:
                log.error(f"Unknown diag attribute {key}")
                sys.exit(1)
            self.jumpstart_source_attributes['diag_attributes'][
                key] = diag_attributes[key]

        # Override the diag attributes with the values specified on the
        # command line.
        if override_diag_attributes is not None:
            for override in override_diag_attributes:
                attribute_name = override.split("=")[0]
                attribute_value = override.split("=")[1]
                if attribute_value in ["True", "true"]:
                    attribute_value = True
                elif attribute_value in ["False", "false"]:
                    attribute_value = False
                self.jumpstart_source_attributes['diag_attributes'][
                    attribute_name] = attribute_value
                log.warning(
                    f"Command line overriding {attribute_name} with {attribute_value}."
                )

        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_jumpstart_rcode_and_machine_mode_text_section_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])

        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = sorted(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'],
                key=lambda x: x['pa'],
                reverse=False)

        self.sanity_check_diag_attributes()

        # Add a guard page between the diag sections and the jumpstart infrastructure sections.
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_guard_page_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])

        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_jumpstart_umode_text_section_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_jumpstart_umode_data_section_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])

        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_bss_and_rodata_sections_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_jumpstart_supervisor_text_section_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_jumpstart_privileged_data_section_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = self.add_guard_page_to_mappings(
                self.jumpstart_source_attributes['diag_attributes']
                ['mappings'])

        self.create_pagetables()
        self.create_pmarr_regions()

        self.sanity_check_memory_map()

    def sanity_check_memory_map(self):
        for mapping in self.jumpstart_source_attributes['diag_attributes'][
                'mappings']:
            if 'no_pte_allocation' in mapping and mapping[
                    'no_pte_allocation'] is True:
                pte_attributes = ['xwr', 'umode', 'va']
                # if the mapping has a no_pte_allocation attribute, then
                # it should not have any xwr or umode bits set.
                assert (not any(x in mapping for x in pte_attributes))

        # check that the memory mappings don't overlap
        # the mappings are sorted by the physical address at this point.
        last_mapping = None
        for mapping in self.jumpstart_source_attributes['diag_attributes'][
                'mappings']:

            if last_mapping is None:
                last_mapping = mapping
                continue

            last_mapping_size = last_mapping['page_size'] * last_mapping[
                'num_pages']
            if mapping['pmarr_memory_type'] != last_mapping[
                    'pmarr_memory_type'] and last_mapping_size < PmarrAttributes.minimum_size:
                #  These mappings will fall into different PMARR regions which have a minimum size of 1M.
                last_mapping_size = PmarrAttributes.minimum_size

            last_mapping_end_address = last_mapping['pa'] + last_mapping_size

            if mapping['pa'] < last_mapping_end_address:
                log.error(
                    f"Memory mapping {mapping} overlaps with {last_mapping}")
                sys.exit(1)

            last_mapping = mapping

    def sanity_check_diag_attributes(self):
        assert ('satp_mode'
                in self.jumpstart_source_attributes['diag_attributes'])
        assert (
            self.jumpstart_source_attributes['diag_attributes']['satp_mode']
            in self.pt_attributes.mode_attributes)

    def create_pmarr_regions(self):
        self.pmarr_regions = []

        # Use PMARR_0 to handle the jumpstart M-mode region. This region
        # doesn't show up in the diag_attribute['mappings'] so explicitly add it
        # to the pmarr_regions.
        pmarr_0_region = PmarrRegion(
            self.jumpstart_source_attributes['diag_attributes']
            ['machine_mode_start_address'],
            self.jumpstart_source_attributes['diag_attributes']
            ['machine_mode_start_address'] + PmarrAttributes.minimum_size,
            "wb")
        self.pmarr_regions.append(pmarr_0_region)

        for mapping in self.jumpstart_source_attributes['diag_attributes'][
                'mappings']:
            if 'pmarr_memory_type' not in mapping:
                log.error("pmarr_memory_type is not specified in the mapping")
                sys.exit(1)

            mapping_size = mapping['page_size'] * mapping['num_pages']

            pmarr_memory_type = mapping['pmarr_memory_type']

            matching_pmarr_region = None
            for pmarr_region in self.pmarr_regions:
                if pmarr_region.can_add_to_region(mapping['pa'],
                                                  mapping['pa'] + mapping_size,
                                                  pmarr_memory_type):
                    matching_pmarr_region = pmarr_region
                    break
            if matching_pmarr_region is None:
                new_pmarr_region = PmarrRegion(mapping['pa'],
                                               mapping['pa'] + mapping_size,
                                               pmarr_memory_type)
                self.pmarr_regions.append(new_pmarr_region)
            else:
                matching_pmarr_region.add_to_region(
                    mapping['pa'], mapping['pa'] + mapping_size)

    def add_after_mapping(self,
                          mappings,
                          previous_mapping_id,
                          xwr,
                          umode,
                          num_pages,
                          pmarr_memory_type,
                          linker_script_section,
                          no_pte_allocation=False):
        # We expect that the mappings are sorted by the virtual address.
        updated_mappings = mappings.copy()
        previous_mapping = updated_mappings[previous_mapping_id]
        new_mapping = {}

        previous_mapping_size = previous_mapping[
            'page_size'] * previous_mapping['num_pages']
        if previous_mapping[
                'pmarr_memory_type'] != pmarr_memory_type and previous_mapping_size < PmarrAttributes.minimum_size:
            log.debug(
                f"Placing new mapping {previous_mapping_size} bytes after {previous_mapping} to account for PMARR minimum size of {PmarrAttributes.minimum_size}"
            )
            previous_mapping_size = PmarrAttributes.minimum_size

        # If the last mapping is a no_pte_allocation mapping, then it
        # won't have a VA.
        assert ('va' in previous_mapping
                or ('no_pte_allocation' in previous_mapping
                    and previous_mapping['no_pte_allocation'] is True))
        if 'va' not in previous_mapping:
            previous_mapping_va = previous_mapping['pa']
        else:
            previous_mapping_va = previous_mapping['va']

        new_mapping['va'] = previous_mapping_va + previous_mapping_size
        new_mapping['pa'] = previous_mapping['pa'] + previous_mapping_size

        new_mapping['xwr'] = xwr
        new_mapping['umode'] = umode
        new_mapping['page_size'] = 1 << self.get_attribute('page_offset')
        new_mapping['num_pages'] = num_pages
        new_mapping['pmarr_memory_type'] = pmarr_memory_type
        new_mapping['linker_script_section'] = linker_script_section
        new_mapping['no_pte_allocation'] = no_pte_allocation

        # make sure that the new mapping doesn't overlap with the next
        # one if it exists.
        if (previous_mapping_id + 1) < len(updated_mappings):
            next_mapping = updated_mappings[previous_mapping_id + 1]
            assert ((new_mapping['pa'] +
                     (new_mapping['page_size'] * new_mapping['num_pages'])) <=
                    next_mapping['pa'])

        updated_mappings.insert(previous_mapping_id + 1, new_mapping)
        return updated_mappings

    def add_pagetable_section_to_mappings(self, mappings):
        # Add an additional mapping after the last mapping for the pagetables
        updated_mappings = self.add_after_mapping(
            mappings,
            len(mappings) - 1, "0b001", "0b0",
            self.num_pages_available_for_PT_allocation, 'wb',
            '.jumpstart.rodata.pagetables')
        self.PT_section_start_address = updated_mappings[-1]['pa']
        return updated_mappings

    def add_jumpstart_supervisor_text_section_to_mappings(self, mappings):
        num_jumpstart_text_pages = 0
        for page_count in self.jumpstart_source_attributes[
                'jumpstart_supervisor_text_page_counts']:
            num_jumpstart_text_pages += self.jumpstart_source_attributes[
                'jumpstart_supervisor_text_page_counts'][page_count]
        updated_mappings = self.add_after_mapping(
            mappings,
            len(mappings) - 1, "0b101", "0b0", num_jumpstart_text_pages, 'wb',
            '.jumpstart.text.supervisor')
        return updated_mappings

    def add_jumpstart_privileged_data_section_to_mappings(self, mappings):
        num_jumpstart_data_pages = 0
        for page_count in self.jumpstart_source_attributes[
                'jumpstart_privileged_data_page_counts']:
            num_jumpstart_data_pages += self.jumpstart_source_attributes[
                'jumpstart_privileged_data_page_counts'][page_count]

        updated_mappings = self.add_after_mapping(
            mappings,
            len(mappings) - 1, "0b011", "0b0", num_jumpstart_data_pages, 'wb',
            '.jumpstart.data.privileged')
        return updated_mappings

    def add_bss_and_rodata_sections_to_mappings(self, mappings):
        updated_mappings = self.add_after_mapping(mappings,
                                                  len(mappings) - 1, "0b011",
                                                  "0b0", 1, 'wb', '.bss')
        updated_mappings = self.add_after_mapping(updated_mappings,
                                                  len(updated_mappings) - 1,
                                                  "0b001", "0b0", 1, 'wb',
                                                  '.rodata')
        return updated_mappings

    def add_jumpstart_umode_text_section_to_mappings(self, mappings):
        num_jumpstart_text_pages = 0
        for page_count in self.jumpstart_source_attributes[
                'jumpstart_umode_text_page_counts']:
            num_jumpstart_text_pages += self.jumpstart_source_attributes[
                'jumpstart_umode_text_page_counts'][page_count]
        updated_mappings = self.add_after_mapping(mappings,
                                                  len(mappings) - 1, "0b101",
                                                  "0b1",
                                                  num_jumpstart_text_pages,
                                                  'wb',
                                                  '.jumpstart.text.umode')
        return updated_mappings

    def add_jumpstart_umode_data_section_to_mappings(self, mappings):
        num_jumpstart_data_pages = 0
        for page_count in self.jumpstart_source_attributes[
                'jumpstart_umode_data_page_counts']:
            num_jumpstart_data_pages += self.jumpstart_source_attributes[
                'jumpstart_umode_data_page_counts'][page_count]

        updated_mappings = self.add_after_mapping(mappings,
                                                  len(mappings) - 1, "0b011",
                                                  "0b1",
                                                  num_jumpstart_data_pages,
                                                  'wb',
                                                  '.jumpstart.data.umode')
        return updated_mappings

    def add_jumpstart_rcode_and_machine_mode_text_section_to_mappings(
            self, mappings):
        # rcode section
        rcode_mapping = {}
        rcode_mapping['pa'] = self.jumpstart_source_attributes[
            'diag_attributes']['rcode_start_address']
        rcode_mapping['page_size'] = 1 << self.get_attribute('page_offset')
        rcode_mapping['num_pages'] = self.jumpstart_source_attributes[
            'jumpstart_rcode_text_page_counts']['num_pages_for_all_text']
        rcode_mapping[
            'linker_script_section'] = ".jumpstart.text.rcode.init,.jumpstart.text.rcode"
        rcode_mapping['pmarr_memory_type'] = "wb"
        rcode_mapping['no_pte_allocation'] = True
        mappings.append(rcode_mapping)

        # Add a guard page mapping to catch linker script overruns of rcode
        rcode_guard_page_mapping = {}
        rcode_guard_page_mapping['pa'] = rcode_mapping[
            'pa'] + rcode_mapping['page_size'] * rcode_mapping['num_pages']
        rcode_guard_page_mapping['page_size'] = 1 << self.get_attribute(
            'page_offset')
        rcode_guard_page_mapping['num_pages'] = 1
        rcode_guard_page_mapping[
            'linker_script_section'] = f".jumpstart.guard_page.{self.num_guard_pages_generated}"
        self.num_guard_pages_generated += 1
        rcode_guard_page_mapping['pmarr_memory_type'] = "wb"
        rcode_guard_page_mapping['no_pte_allocation'] = True
        mappings.append(rcode_guard_page_mapping)

        # machine mode section
        machine_mode_mapping = {}
        machine_mode_mapping['pa'] = self.jumpstart_source_attributes[
            'diag_attributes']['machine_mode_start_address']
        machine_mode_mapping['page_size'] = 1 << self.get_attribute(
            'page_offset')
        machine_mode_mapping['num_pages'] = self.jumpstart_source_attributes[
            'jumpstart_machine_text_page_counts']['num_pages_for_all_text']
        machine_mode_mapping[
            'linker_script_section'] = ".jumpstart.text.machine.init,.jumpstart.text.machine,.jumpstart.text.machine.end"
        machine_mode_mapping['pmarr_memory_type'] = "wb"
        machine_mode_mapping['no_pte_allocation'] = True
        mappings.append(machine_mode_mapping)

        # Add a guard page mapping to catch linker script overruns of machine_mode
        machine_mode_guard_page_mapping = {}
        machine_mode_guard_page_mapping[
            'pa'] = machine_mode_mapping['pa'] + machine_mode_mapping[
                'page_size'] * machine_mode_mapping['num_pages']
        machine_mode_guard_page_mapping['page_size'] = 1 << self.get_attribute(
            'page_offset')
        machine_mode_guard_page_mapping['num_pages'] = 1
        machine_mode_guard_page_mapping[
            'linker_script_section'] = f".jumpstart.guard_page.{self.num_guard_pages_generated}"
        self.num_guard_pages_generated += 1
        machine_mode_guard_page_mapping['pmarr_memory_type'] = "wb"
        machine_mode_guard_page_mapping['no_pte_allocation'] = True
        mappings.append(machine_mode_guard_page_mapping)

        return mappings

    def add_guard_page_to_mappings(self, mappings):
        # Guard pages have no RWX permissions and are used to detect
        # overflows or underflows in the jumpstart data section
        updated_mappings = self.add_after_mapping(
            mappings,
            len(mappings) - 1, "0b000", "0b0", 1, 'wb',
            f'.jumpstart.guard_page.{self.num_guard_pages_generated}')
        self.num_guard_pages_generated += 1
        return updated_mappings

    def split_mappings_at_page_granularity(self, mappings):
        split_mappings = []
        for entry in mappings:
            if 'no_pte_allocation' in entry and entry[
                    'no_pte_allocation'] is True:
                continue

            va = entry['va']
            pa = entry['pa']
            for _ in range(entry['num_pages']):
                new_entry = entry.copy()
                new_entry['va'] = va
                new_entry['pa'] = va
                new_entry['num_pages'] = 1
                split_mappings.append(new_entry)

                va += entry['page_size']
                pa += entry['page_size']

        return split_mappings

    def get_attribute(self, attribute):
        if attribute in self.pt_attributes.common_attributes:
            return self.pt_attributes.common_attributes[attribute]
        assert (attribute in self.pt_attributes.mode_attributes[
            self.jumpstart_source_attributes['diag_attributes']['satp_mode']])
        return self.pt_attributes.mode_attributes[
            self.jumpstart_source_attributes['diag_attributes']
            ['satp_mode']][attribute]

    def update_pte_region_sparse_memory(self, address, value):
        if address in self.pte_region_sparse_memory:
            assert (self.pte_region_sparse_memory[address] == value)
            log.debug(f"[{hex(address)}] = {hex(value)} (already exists)")
        else:
            self.pte_region_sparse_memory[address] = value
            log.debug(f"[{hex(address)}] = {hex(value)}")

    def get_pte_region_sparse_memory_contents_at(self, address):
        if address in self.pte_region_sparse_memory:
            return self.pte_region_sparse_memory[address]
        return None

    def get_PT_page(self, va, level):
        log.debug(f"get_PT_page({hex(va)}, {level})")
        # look for an existing pagetable page that contains the given VA
        for page in self.PT_pages:
            if page.contains(va, level):
                log.debug(f"Found existing pagetable page {page}")
                return page

        # else allocate a new page
        log.debug(
            f"Allocating new pagetable page for VA {hex(va)} at level {level}")

        if len(self.PT_pages) == self.num_pages_available_for_PT_allocation:
            # Can't create any more pagetable pages
            return None

        PT_page_size = 1 << self.get_attribute('page_offset')
        va_msb = 63
        va_lsb = self.get_attribute('va_vpn_bits')[level][0]
        start_va = extract_bits(va, (va_msb, va_lsb)) << va_lsb
        va_range = 1 << (self.get_attribute('va_vpn_bits')[level][0] + 1)
        new_PT_page = PageTablePage(
            self.PT_section_start_address + PT_page_size * len(self.PT_pages),
            start_va, level, va_range)

        log.debug(f"Allocated new pagetable page {new_PT_page}")

        self.PT_pages.append(new_PT_page)

        return new_PT_page

    # Populates the sparse memory with the pagetable entries and returns the
    # updated mappings with the pagetable section added.
    # Returns None if there are insufficient number of pagetable pages
    # to allocate from.
    def allocate_PT_mappings(self):
        updated_mappings = self.add_pagetable_section_to_mappings(
            self.jumpstart_source_attributes['diag_attributes']['mappings'])

        for entry in self.split_mappings_at_page_granularity(updated_mappings):
            # TODO: support superpages
            assert (entry['page_size'] == 0x1000)

            log.debug(f"Generating PTEs for {entry}")

            current_level = 0

            while current_level < self.get_attribute('num_levels'):
                current_level_PT_page = self.get_PT_page(
                    entry['va'], current_level)
                if (current_level_PT_page is None):
                    log.debug(
                        f"Insufficient pagetable pages to create level {current_level + 1} pagetable for {entry}"
                    )
                    return None

                current_level_range_start = current_level_PT_page.get_sparse_memory_address(
                )
                current_level_range_end = current_level_range_start + (
                    1 << self.get_attribute('page_offset'))

                pte_value = place_bits(
                    0, 1, self.pt_attributes.common_attributes["valid_bit"])

                if current_level < (self.get_attribute('num_levels') - 1):
                    next_level_pagetable = self.get_PT_page(
                        entry['va'], current_level + 1)
                    if next_level_pagetable is None:
                        log.debug(
                            f"Insufficient pagetable pages to create next level {current_level + 1} pagetable for {entry}"
                        )
                        return None

                    next_level_range_start = next_level_pagetable.get_sparse_memory_address(
                    )
                    next_level_range_end = next_level_range_start + (
                        1 << self.get_attribute('page_offset'))

                    next_level_pa = next_level_range_start + extract_bits(
                        entry['va'],
                        self.get_attribute('va_vpn_bits')[current_level]
                    ) * self.get_attribute('pte_size_in_bytes')

                    assert (next_level_pa < next_level_range_end)
                else:
                    xwr_bits = int(entry['xwr'], 2)
                    assert (xwr_bits != 0x2 and xwr_bits != 0x6)
                    pte_value = place_bits(
                        pte_value, xwr_bits,
                        self.pt_attributes.common_attributes["xwr_bits"])

                    if 'umode' in entry:
                        umode_bit = int(entry['umode'], 2)
                        pte_value = place_bits(
                            pte_value, umode_bit,
                            self.pt_attributes.common_attributes["umode_bit"])

                    pte_value = place_bits(
                        pte_value, 1,
                        self.pt_attributes.common_attributes["a_bit"])
                    pte_value = place_bits(
                        pte_value, 1,
                        self.pt_attributes.common_attributes["d_bit"])

                    if 'pbmt_mode' in entry:
                        pbmt_mode = self.pt_attributes.convert_pbmt_mode_string_to_mode(
                            entry['pbmt_mode'])
                        pte_value = place_bits(
                            pte_value, pbmt_mode,
                            self.pt_attributes.common_attributes["pbmt_bits"])

                    next_level_pa = entry['pa']

                for ppn_id in range(len(self.get_attribute('pa_ppn_bits'))):
                    ppn_value = extract_bits(
                        next_level_pa,
                        self.get_attribute('pa_ppn_bits')[ppn_id])
                    pte_value = place_bits(
                        pte_value, ppn_value,
                        self.get_attribute('pte_ppn_bits')[ppn_id])

                pte_address = current_level_range_start + extract_bits(
                    entry['va'],
                    self.get_attribute('va_vpn_bits')
                    [current_level]) * self.get_attribute('pte_size_in_bytes')
                assert (pte_address < current_level_range_end)

                self.update_pte_region_sparse_memory(pte_address, pte_value)

                current_level += 1

        return updated_mappings

    def create_pagetables(self):
        # this is the minimum number of page tables we need.
        self.num_pages_available_for_PT_allocation = self.get_attribute(
            'num_levels')

        while True:
            self.PT_section_start_address = None
            self.PT_pages = []
            self.pte_region_sparse_memory = {}

            updated_mappings = self.allocate_PT_mappings()
            if updated_mappings == None:
                if self.num_pages_available_for_PT_allocation >= self.jumpstart_source_attributes[
                        'diag_attributes']['max_num_pages_for_PT_allocation']:
                    log.error(
                        f"Hit max number of PT pages ({self.jumpstart_source_attributes['diag_attributes']['max_num_pages_for_PT_allocation']}) available to create pagetables"
                    )
                    sys.exit(1)

                self.num_pages_available_for_PT_allocation += 1
                log.debug(
                    f"Increasing the number of pagetable pages to {self.num_pages_available_for_PT_allocation} and retrying PT allocation."
                )
                continue

            break

        # Update the existing mappings as we've added new mappings
        # for the page table region.
        self.jumpstart_source_attributes['diag_attributes'][
            'mappings'] = updated_mappings

        # Make sure that we have the first and last addresses set so that we
        # know the range of the page table memory when generating the
        # page table section in the assembly file.
        assert (self.PT_section_start_address ==
                self.PT_pages[0].get_sparse_memory_address())
        pte_region_sparse_memory_start = self.PT_pages[
            0].get_sparse_memory_address()
        PT_page_size = 1 << self.get_attribute('page_offset')
        pte_region_sparse_memory_end = self.PT_pages[
            len(self.PT_pages) - 1].get_sparse_memory_address() + PT_page_size

        if pte_region_sparse_memory_start not in self.pte_region_sparse_memory:
            self.pte_region_sparse_memory[pte_region_sparse_memory_start] = 0
        if pte_region_sparse_memory_end not in self.pte_region_sparse_memory:
            self.pte_region_sparse_memory[
                pte_region_sparse_memory_end -
                self.get_attribute('pte_size_in_bytes')] = 0

    def generate_linker_script(self, output_linker_script):
        with open(output_linker_script, 'w') as file:
            file.write(
                f"/* This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml} */\n"
            )
            file.write(
                f"/* SATP.Mode is {self.jumpstart_source_attributes['diag_attributes']['satp_mode']} */\n\n"
            )
            file.write('OUTPUT_ARCH( "riscv" )\n')
            file.write('ENTRY(_rcode_start)\n\n')

            file.write('SECTIONS\n{\n')
            defined_sections = []

            # The entries are already sorted by VA
            # we also expect that the pages for the same section
            # are in consecutive order when the VAs are sorted.
            for entry in self.jumpstart_source_attributes['diag_attributes'][
                    'mappings']:
                if 'linker_script_section' not in entry:
                    # We don't generate linker script sections for entries
                    # that don't have a linker_script_section attribute.
                    continue

                file.write(f"   /* {entry['linker_script_section']}: \n")
                file.write(
                    f"       PA Range: {hex(entry['pa'])} - {hex(entry['pa'] + entry['num_pages'] * entry['page_size'])}\n"
                )
                file.write(f"   */\n")
                file.write(f"   . = {hex(entry['pa'])};\n")

                linker_script_sections = entry['linker_script_section']
                file.write(f"   {linker_script_sections.split(',')[0]} : {{\n")
                for section_name in linker_script_sections.split(','):
                    assert (section_name not in defined_sections)
                    file.write(f"      *({section_name})\n")
                    defined_sections.append(section_name)
                file.write(f"   }}\n\n")
            file.write('\n}\n')

            file.close()

    def generate_diag_attribute_functions(self, file_descriptor):
        self.generate_boolean_diag_attribute_functions(
            file_descriptor, ['start_test_in_machine_mode', 'in_qemu_mode'])
        self.generate_get_active_hart_mask_function(file_descriptor)

        if self.jumpstart_source_attributes['diag_attributes'][
                'in_qemu_mode'] == True and self.jumpstart_source_attributes[
                    'diag_attributes']['active_hart_mask'] != '0b1111':
            log.error(
                f"Unsupported active_hart_mask {self.jumpstart_source_attributes['diag_attributes']['active_hart_mask']} for QEMU mode. active_hart_mask must be 0b1111."
            )
            sys.exit(1)

    def generate_boolean_diag_attribute_functions(self, file_descriptor,
                                                  boolean_attributes):
        for attribute in boolean_attributes:
            file_descriptor.write('.section .jumpstart.text.machine, "ax"\n\n')
            file_descriptor.write(f".global {attribute}\n")
            file_descriptor.write(f"{attribute}:\n\n")

            attribute_value = int(
                self.jumpstart_source_attributes['diag_attributes'][attribute])

            file_descriptor.write(f"   li a0, {attribute_value}\n")
            file_descriptor.write(f"   ret\n\n\n")

    def generate_get_active_hart_mask_function(self, file_descriptor):
        modes = ['machine', 'supervisor']
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.text.{mode}, "ax"\n\n')
            file_descriptor.write(
                f".global get_active_hart_mask_from_{mode}_mode\n")
            file_descriptor.write(
                f"get_active_hart_mask_from_{mode}_mode:\n\n")
            active_hart_mask = 1  # hart 0 is active by default.
            if 'active_hart_mask' in self.jumpstart_source_attributes[
                    'diag_attributes']:
                active_hart_mask = int(
                    self.jumpstart_source_attributes['diag_attributes']
                    ['active_hart_mask'], 2)

            assert (
                active_hart_mask.bit_count() <=
                self.jumpstart_source_attributes['max_num_harts_supported'])

            file_descriptor.write(f"   li a0, {active_hart_mask}\n")
            file_descriptor.write(f"   ret\n\n\n")

    def generate_mmu_functions(self, file_descriptor):
        file_descriptor.write(
            f"# SATP.Mode is {self.jumpstart_source_attributes['diag_attributes']['satp_mode']}\n\n"
        )
        file_descriptor.write(
            f"#define DIAG_SATP_MODE {self.get_attribute('satp_mode')}\n")

        modes = ['machine', 'supervisor']
        for mode in modes:
            file_descriptor.write(f'.section .jumpstart.text.{mode}, "ax"\n\n')

            file_descriptor.write(
                f".global get_diag_satp_mode_from_{mode}_mode\n")
            file_descriptor.write(f"get_diag_satp_mode_from_{mode}_mode:\n\n")
            file_descriptor.write(f"    li   a0, DIAG_SATP_MODE\n")
            file_descriptor.write(f"    ret\n\n\n")

            file_descriptor.write(f".global enable_mmu_from_{mode}_mode\n")
            file_descriptor.write(f"enable_mmu_from_{mode}_mode:\n\n")
            file_descriptor.write(f"    li   t0, DIAG_SATP_MODE\n")
            file_descriptor.write(f"    slli  t0, t0, SATP_MODE_LSB\n")
            file_descriptor.write(
                f"    la t1, {self.pt_attributes.pt_start_label}\n")
            file_descriptor.write(f"    srai t1, t1, PAGE_OFFSET\n")
            file_descriptor.write(f"    add  t1, t1, t0\n")
            file_descriptor.write(f"    csrw  satp, t1\n")
            file_descriptor.write(f"    sfence.vma\n")
            file_descriptor.write(f"    ret\n")

    def generate_pmarr_functions(self, file_descriptor):
        file_descriptor.write('.section .jumpstart.text.rcode, "ax"\n\n')
        file_descriptor.write("\n")
        file_descriptor.write(".global setup_pmarr\n")
        file_descriptor.write("setup_pmarr:\n\n")

        pmarr_reg_id = 0
        for region in self.pmarr_regions:
            region.generate_pmarr_region_setup_code(file_descriptor,
                                                    pmarr_reg_id)
            pmarr_reg_id += 1
            assert (pmarr_reg_id < PmarrAttributes.num_registers)
        file_descriptor.write(f"   ret\n\n\n")
        file_descriptor.write("\n")

    def generate_page_table_data(self, file_descriptor):
        file_descriptor.write('.section .jumpstart.rodata.pagetables, "a"\n\n')
        file_descriptor.write(f".global {self.pt_attributes.pt_start_label}\n")
        file_descriptor.write(f"{self.pt_attributes.pt_start_label}:\n\n")

        pagetable_filled_memory_addresses = list(
            sorted(self.pte_region_sparse_memory.keys()))

        pte_size_in_bytes = self.pt_attributes.mode_attributes[
            self.jumpstart_source_attributes['diag_attributes']
            ['satp_mode']]['pte_size_in_bytes']
        last_filled_address = None
        for address in pagetable_filled_memory_addresses:
            if last_filled_address is not None and address != (
                    last_filled_address + pte_size_in_bytes):
                file_descriptor.write(
                    f".skip {hex(address - (last_filled_address + pte_size_in_bytes))}\n"
                )
            log.debug(
                f"Writing [{hex(address)}] = {hex(self.pte_region_sparse_memory[address])}"
            )
            file_descriptor.write(f"\n# [{hex(address)}]\n")
            file_descriptor.write(
                f".{pte_size_in_bytes}byte {hex(self.pte_region_sparse_memory[address])}\n"
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
            file_descriptor.write(f".zero 4096\n\n")

    def generate_assembly_file(self, output_assembly_file):
        with open(output_assembly_file, 'w') as file:
            file.write(
                f"# This file is auto-generated by {sys.argv[0]} from {self.diag_attributes_yaml}\n"
            )

            file.write("#include \"jumpstart_defines.h\"\n\n")

            self.generate_diag_attribute_functions(file)

            self.generate_mmu_functions(file)
            self.generate_pmarr_functions(file)

            self.generate_page_table_data(file)

            self.generate_guard_pages(file)

            file.close()

    def translate_VA(self, va):
        log.info(
            f"Translating VA {hex(va)}. SATP.Mode = {self.jumpstart_source_attributes['diag_attributes']['satp_mode']}"
        )

        # Step 1
        assert (self.PT_section_start_address ==
                self.PT_pages[0].get_sparse_memory_address())
        a = self.PT_pages[0].get_sparse_memory_address()

        current_level = 0
        pte_value = 0

        # Step 2
        while True:
            log.info(f"    a = {hex(a)}; current_level = {current_level}")
            pte_address = a + extract_bits(
                va,
                self.get_attribute('va_vpn_bits')
                [current_level]) * self.get_attribute('pte_size_in_bytes')
            pte_value = self.get_pte_region_sparse_memory_contents_at(
                pte_address)
            if pte_value == None:
                log.error(f"Expected PTE at {hex(pte_address)} is not present")
                sys.exit(1)

            log.info(
                f"    level{current_level} PTE: [{hex(pte_address)}] = {hex(pte_value)}"
            )

            if extract_bits(
                    pte_value,
                    self.pt_attributes.common_attributes['valid_bit']) == 0:
                log.error(f"PTE at {hex(pte_address)} is not valid")
                sys.exit(1)

            xwr = extract_bits(
                pte_value, self.pt_attributes.common_attributes['xwr_bits'])
            if (xwr & 0x3) == 0x2:
                log.error(f"PTE at {hex(pte_address)} has R=0 and W=1")
                sys.exit(1)

            a = 0
            for ppn_id in range(len(self.get_attribute('pte_ppn_bits'))):
                ppn_value = extract_bits(
                    pte_value,
                    self.get_attribute('pte_ppn_bits')[ppn_id])
                a = place_bits(a, ppn_value,
                               self.get_attribute('pa_ppn_bits')[ppn_id])

            if (xwr & 0x6) or (xwr & 0x1):
                log.info(f"    This is a Leaf PTE")
                break
            else:
                if extract_bits(
                        pte_value,
                        self.pt_attributes.common_attributes['a_bit']) != 0:
                    log.error(f"PTE has A=1 but is not a Leaf PTE")
                    sys.exit(1)
                elif extract_bits(
                        pte_value,
                        self.pt_attributes.common_attributes['d_bit']) != 0:
                    log.error(f"PTE has D=1 but is not a Leaf PTE")
                    sys.exit(1)

            current_level += 1
            if current_level >= self.get_attribute('num_levels'):
                log.error(f"Ran out of levels")
                sys.exit(1)
            continue

        pa = a + extract_bits(va, (self.get_attribute('page_offset'), 0))

        log.info(f"Translated PA = {hex(pa)}")
        log.info(f"    PTE value = {hex(pte_value)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diag_attributes_yaml',
                        help='Diag Attributes YAML file',
                        required=True,
                        type=str)
    parser.add_argument('--jumpstart_source_attributes_yaml',
                        help=f'YAML containing the jumpstart attributes.',
                        required=True,
                        type=str)
    parser.add_argument(
        '--output_assembly_file',
        help='Assembly file to generate with page table mappings',
        required=False,
        type=str)
    parser.add_argument('--output_linker_script',
                        help='Linker script to generate',
                        required=False,
                        type=str)
    parser.add_argument('--override_diag_attributes',
                        help='Overrides the specified diag attributes.',
                        required=False,
                        nargs='+',
                        default=None)
    parser.add_argument('--translate_VA',
                        help='Translate the given VA to PA',
                        required=False,
                        type=lambda x: int(x, 0))
    parser.add_argument('-v',
                        '--verbose',
                        help='Verbose output.',
                        action='store_true',
                        default=False)
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s",
                        level=log.DEBUG)
    else:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s",
                        level=log.INFO)

    if os.path.exists(args.diag_attributes_yaml) is False:
        raise Exception(
            f"Diag Attributes file {args.diag_attributes_yaml} not found")

    if os.path.exists(args.jumpstart_source_attributes_yaml) is False:
        raise Exception(
            f"Jumpstart Attributes file {args.jumpstart_source_attributes_yaml} not found"
        )

    pagetables = DiagAttributes(args.jumpstart_source_attributes_yaml,
                                args.diag_attributes_yaml,
                                args.override_diag_attributes)

    if args.output_assembly_file is not None:
        pagetables.generate_assembly_file(args.output_assembly_file)
    if args.output_linker_script is not None:
        pagetables.generate_linker_script(args.output_linker_script)

    if args.translate_VA is not None:
        pagetables.translate_VA(args.translate_VA)


if __name__ == '__main__':
    main()
