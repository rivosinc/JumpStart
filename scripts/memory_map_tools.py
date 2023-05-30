#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

import argparse
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


class PageTables:
    max_num_JumpStart_data_pages = 5

    common_attributes = {
        "page_offset": 12,
        "valid_bit": (0, 0),
        "xwr_bits": (3, 1),
        "global_bit": (5, 5),
        "a_bit": (6, 6),
        "d_bit": (7, 7),
        "satp_mode_lsb": 60,
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

    def __init__(self, memory_map_file):
        if os.path.exists(memory_map_file) is False:
            raise Exception(
                f"Memory map file {memory_map_file} does not exist")

        self.memory_map_file = memory_map_file
        self.max_num_pages_for_PT_allocation = 3

        with open(memory_map_file, "r") as f:
            self.memory_map = yaml.safe_load(f)

            assert ('satp_mode' in self.memory_map)
            assert (self.memory_map['satp_mode'] in self.mode_attributes)

            if 'max_num_pages_for_PT_allocation' in self.memory_map:
                self.max_num_pages_for_PT_allocation = self.memory_map[
                    'max_num_pages_for_PT_allocation']

            self.memory_map['mappings'] = sorted(self.memory_map['mappings'],
                                                 key=lambda x: x['va'],
                                                 reverse=False)
            f.close()

        self.create_pagetables()

    def add_pagetable_section_to_mappings(self, mappings):
        # Add an additional mapping after the last mapping for the pagetables
        updated_mappings = mappings.copy()
        last_mapping = updated_mappings[-1]
        pagetable_mapping = {}
        self.PT_section_start_address = last_mapping['va'] + (
            last_mapping['page_size'] * last_mapping['num_pages'])
        pagetable_mapping['va'] = self.PT_section_start_address
        pagetable_mapping['pa'] = last_mapping['pa'] + (
            last_mapping['page_size'] * last_mapping['num_pages'])
        pagetable_mapping['xwr'] = "0b001"
        pagetable_mapping['page_size'] = 1 << self.get_attribute('page_offset')
        pagetable_mapping[
            'num_pages'] = self.num_pages_available_for_PT_allocation
        pagetable_mapping['section'] = '.rodata.jumpstart.pagetables'
        updated_mappings.append(pagetable_mapping)

        return updated_mappings

    def add_jumpstart_data_section_to_mappings(self, mappings):
        updated_mappings = mappings.copy()
        last_mapping = updated_mappings[-1]
        jumpstart_data_section_mapping = {}
        jumpstart_data_section_mapping['va'] = last_mapping['va'] + (
            last_mapping['page_size'] * last_mapping['num_pages'])
        jumpstart_data_section_mapping['pa'] = last_mapping['pa'] + (
            last_mapping['page_size'] * last_mapping['num_pages'])
        jumpstart_data_section_mapping['xwr'] = "0b011"
        jumpstart_data_section_mapping['page_size'] = 1 << self.get_attribute(
            'page_offset')
        jumpstart_data_section_mapping[
            'num_pages'] = self.max_num_JumpStart_data_pages
        jumpstart_data_section_mapping['section'] = '.data.jumpstart'
        updated_mappings.append(jumpstart_data_section_mapping)

        return updated_mappings

    def split_mappings_at_page_granularity(self, mappings):
        split_mappings = []
        for entry in mappings:
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
        if attribute in self.common_attributes:
            return self.common_attributes[attribute]
        assert (attribute
                in self.mode_attributes[self.memory_map['satp_mode']])
        return self.mode_attributes[self.memory_map['satp_mode']][attribute]

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
    # allocate from.
    def allocate_PT_mappings(self):
        updated_mappings = self.add_jumpstart_data_section_to_mappings(
            self.memory_map['mappings'])
        updated_mappings = self.add_pagetable_section_to_mappings(
            updated_mappings)

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

                pte_value = place_bits(0, 1,
                                       self.common_attributes["valid_bit"])

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
                    pte_value = place_bits(pte_value, xwr_bits,
                                           self.common_attributes["xwr_bits"])

                    pte_value = place_bits(pte_value, 1,
                                           self.common_attributes["a_bit"])
                    pte_value = place_bits(pte_value, 1,
                                           self.common_attributes["d_bit"])

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
                if self.num_pages_available_for_PT_allocation >= self.max_num_pages_for_PT_allocation:
                    log.error(
                        f"Hit max number of PT pages ({self.max_num_pages_for_PT_allocation}) available to create pagetables"
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
        self.memory_map['mappings'] = updated_mappings

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
                f"/* This file is auto-generated by {sys.argv[0]} from {self.memory_map_file} */\n"
            )
            file.write(
                f"/* SATP.Mode is {self.memory_map['satp_mode']} */\n\n")
            file.write('OUTPUT_ARCH( "riscv" )\n')
            file.write('ENTRY(_start)\n\n')

            file.write('SECTIONS\n{\n')

            # The entries are already sorted by VA
            # we also expect that the pages for the same section
            # are in consecutive order when the VAs are sorted.
            previous_section = None
            for entry in self.memory_map['mappings']:
                if previous_section == entry['section']:
                    continue

                file.write(f"   . = {hex(entry['va'])};\n")
                file.write(f"   {entry['section']} : {{\n")
                if entry['section'] == ".text":
                    file.write(f"      *(.text.jumpstart.init)\n")
                    file.write(f"      *(.text.jumpstart)\n")
                file.write(f"      *({entry['section']})\n")
                file.write(f"   }}\n\n")

                previous_section = entry['section']
            file.write('\n}\n')

            file.close()

    def generate_assembly_file(self, output_assembly_file):
        pt_start_label = "pagetables_start"

        with open(output_assembly_file, 'w') as file:
            file.write(
                f"# This file is auto-generated by {sys.argv[0]} from {self.memory_map_file}\n"
            )
            file.write(f"# SATP.Mode is {self.memory_map['satp_mode']}\n\n")

            file.write(".section .text\n\n")
            file.write(
                f"#define PAGE_OFFSET {self.get_attribute('page_offset')}\n")
            file.write(
                f"#define SATP_MODE {self.get_attribute('satp_mode')}\n")
            file.write(
                f"#define SATP_MODE_LSB {self.get_attribute('satp_mode_lsb')}\n\n"
            )
            file.write(".global get_diag_satp_ppn\n")
            file.write("get_diag_satp_ppn:\n\n")
            file.write(f"   la a0, {pt_start_label}\n")
            file.write(f"   srai a0, a0, PAGE_OFFSET\n")
            file.write(f"   ret\n\n\n")

            file.write(".global get_page_offset\n")
            file.write("get_page_offset:\n\n")
            file.write(f"   li   a0, PAGE_OFFSET\n")
            file.write(f"   ret\n\n\n")

            file.write(".global get_diag_satp_mode_lsb\n")
            file.write("get_diag_satp_mode_lsb:\n\n")
            file.write(f"   li   a0, SATP_MODE_LSB\n")
            file.write(f"   ret\n\n\n")

            file.write(".global get_diag_satp_mode\n")
            file.write("get_diag_satp_mode:\n\n")
            file.write(f"   li   a0, SATP_MODE\n")
            file.write(f"   ret\n\n\n")

            file.write(".section .rodata.jumpstart.pagetables\n\n")
            file.write(f".global {pt_start_label}\n")
            file.write(f"{pt_start_label}:\n\n")

            pagetable_filled_memory_addresses = list(
                sorted(self.pte_region_sparse_memory.keys()))

            pte_size_in_bytes = self.mode_attributes[
                self.memory_map['satp_mode']]['pte_size_in_bytes']
            last_filled_address = None
            for address in pagetable_filled_memory_addresses:
                if last_filled_address is not None and address != (
                        last_filled_address + pte_size_in_bytes):
                    file.write(
                        f".skip {hex(address - (last_filled_address + pte_size_in_bytes))}\n"
                    )
                log.debug(
                    f"Writing [{hex(address)}] = {hex(self.pte_region_sparse_memory[address])}"
                )
                file.write(f"\n# [{hex(address)}]\n")
                file.write(
                    f".{pte_size_in_bytes}byte {hex(self.pte_region_sparse_memory[address])}\n"
                )

                last_filled_address = address

            file.close()

    def translate_VA(self, va):
        log.info(
            f"Translating VA {hex(va)}. SATP.Mode = {self.memory_map['satp_mode']}"
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

            if extract_bits(pte_value,
                            self.common_attributes['valid_bit']) == 0:
                log.error(f"PTE at {hex(pte_address)} is not valid")
                sys.exit(1)

            xwr = extract_bits(pte_value, self.common_attributes['xwr_bits'])
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
                if extract_bits(pte_value,
                                self.common_attributes['a_bit']) != 0:
                    log.error(f"PTE has A=1 but is not a Leaf PTE")
                    sys.exit(1)
                elif extract_bits(pte_value,
                                  self.common_attributes['d_bit']) != 0:
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
    parser.add_argument('--memory_map_file',
                        help='Memory Map YAML file',
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

    pagetables = PageTables(args.memory_map_file)

    if args.output_assembly_file is not None:
        pagetables.generate_assembly_file(args.output_assembly_file)
    if args.output_linker_script is not None:
        pagetables.generate_linker_script(args.output_linker_script)

    if args.translate_VA is not None:
        pagetables.translate_VA(args.translate_VA)


if __name__ == '__main__':
    main()
