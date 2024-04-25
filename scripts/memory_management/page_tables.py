# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import math
import sys

from data_structures import BitField

from .page_size import PageSize


class PbmtMode(enum.IntEnum):
    PMA = 0
    NC = 1
    IO = 2


class PageTableAttributes:
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
            "page_sizes": [PageSize.SIZE_1G, PageSize.SIZE_2M, PageSize.SIZE_4K],
        },
        "sv48": {
            "satp_mode": 9,
            "pte_size_in_bytes": 8,
            "num_levels": 4,
            "va_vpn_bits": [(47, 39), (38, 30), (29, 21), (20, 12)],
            "pa_ppn_bits": [(55, 39), (38, 30), (29, 21), (20, 12)],
            "pte_ppn_bits": [(53, 37), (36, 28), (27, 19), (18, 10)],
            "page_sizes": [
                PageSize.SIZE_512G,
                PageSize.SIZE_1G,
                PageSize.SIZE_2M,
                PageSize.SIZE_4K,
            ],
        },
    }

    def get_attribute(self, attribute, mode):
        if attribute in self.common_attributes:
            return self.common_attributes[attribute]

        assert mode is not None
        assert attribute in self.mode_attributes[mode]
        return self.mode_attributes[mode][attribute]

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


class PageTablePage:
    def __init__(self, page_pa, va, satp_mode, level):
        # Location of the page table page in physical memory
        self.page_pa = page_pa

        start_va_lsb = PageTableAttributes.mode_attributes[satp_mode]["va_vpn_bits"][level][0] + 1
        start_va = (va >> start_va_lsb) << start_va_lsb
        va_range_in_bytes = 1 << (
            PageTableAttributes.mode_attributes[satp_mode]["va_vpn_bits"][level][0] + 1
        )
        # The start VA for the address range covered by this page table page
        # should be a multiple of the size of the area it covers.
        assert start_va == (math.floor(va / va_range_in_bytes)) * va_range_in_bytes

        self.start_va = start_va
        self.level = level
        self.range_in_bytes = va_range_in_bytes

    def __str__(self):
        return f"PageTablePage: page_pa={hex(self.page_pa)}, start_va={hex(self.start_va)}, level={hex(self.level)}, range_in_bytes={hex(self.range_in_bytes)}"

    def get_page_pa(self):
        return self.page_pa

    def get_level(self):
        return self.level

    def contains(self, va, level):
        if level != self.level:
            return False
        if va >= self.start_va and va < (self.start_va + self.range_in_bytes):
            return True
        return False


class PageTables:
    def __init__(self, satp_mode, max_num_pages_for_pagetables, memory_mappings):
        # List of PageTablePage objects
        self.pages = []
        self.satp_mode = satp_mode
        self.max_num_pages_for_pagetables = max_num_pages_for_pagetables

        self.asm_label = "pagetables_start"
        self.attributes = PageTableAttributes()

        self.pte_memory = {}

        self.start_address = None
        for mapping in memory_mappings:
            if mapping.get_field(
                "linker_script_section"
            ) is not None and "pagetables" in mapping.get_field("linker_script_section"):
                self.start_address = mapping.get_field("pa")
                break

        if self.start_address is None:
            log.error("No pagetables section found in memory mappings")
            sys.exit(1)

        self.create_pagetables_for_mappings(memory_mappings)

    def get_asm_label(self):
        return self.asm_label

    def get_attribute(self, attribute):
        return self.attributes.get_attribute(attribute, self.satp_mode)

    def get_pte_addresses(self):
        return self.pte_memory.keys()

    def get_pte(self, address):
        return self.pte_memory[address]

    def get_page(self, va, level):
        log.debug(f"get_page_table_page({hex(va)}, {level})")
        assert self.start_address is not None
        # look for an existing pagetable page that contains the given VA
        for page in self.pages:
            if page.contains(va, level):
                log.debug(f"Found existing pagetable page {page}")
                return page

        # else allocate a new page
        log.debug(f"Allocating new pagetable page for VA {hex(va)} at level {level}")

        if len(self.pages) == self.max_num_pages_for_pagetables:
            # Can't create any more pagetable pages
            log.error(
                f"Insufficient pagetable pages (num_pages_for_jumpstart_smode_pagetables = {self.max_num_pages_for_pagetables}) to create level {level + 1} pagetable for VA {hex(va)}"
            )
            sys.exit(1)

        new_page = PageTablePage(
            self.start_address + PageSize.SIZE_4K * len(self.pages), va, self.satp_mode, level
        )

        log.debug(f"Allocated new page table page {new_page}")

        self.pages.append(new_page)

        return new_page

    def translate_VA(self, va):
        log.info(f"Translating VA {hex(va)}. SATP.Mode = {self.satp_mode}")

        # Step 1
        assert self.start_address == self.pages[0].get_page_pa()
        a = self.pages[0].get_page_pa()

        current_level = 0
        pte_value = 0

        # Step 2
        while True:
            log.info(f"    a = {hex(a)}; current_level = {current_level}")
            pte_address = a + BitField.extract_bits(
                va, self.get_attribute("va_vpn_bits")[current_level]
            ) * self.get_attribute("pte_size_in_bytes")
            pte_value = self.read_sparse_memory(pte_address)
            if pte_value is None:
                log.error(f"Expected PTE at {hex(pte_address)} is not present")
                sys.exit(1)

            log.info(f"    level{current_level} PTE: [{hex(pte_address)}] = {hex(pte_value)}")

            if (
                BitField.extract_bits(pte_value, self.attributes.common_attributes["valid_bit"])
                == 0
            ):
                log.error(f"PTE at {hex(pte_address)} is not valid")
                sys.exit(1)

            xwr = BitField.extract_bits(pte_value, self.attributes.common_attributes["xwr_bits"])
            if (xwr & 0x3) == 0x2:
                log.error(f"PTE at {hex(pte_address)} has R=0 and W=1")
                sys.exit(1)

            a = 0
            for ppn_id in range(len(self.get_attribute("pte_ppn_bits"))):
                ppn_value = BitField.extract_bits(
                    pte_value, self.get_attribute("pte_ppn_bits")[ppn_id]
                )
                a = BitField.place_bits(a, ppn_value, self.get_attribute("pa_ppn_bits")[ppn_id])

            if (xwr & 0x6) or (xwr & 0x1):
                log.info("    This is a Leaf PTE")
                break
            else:
                if (
                    BitField.extract_bits(pte_value, self.attributes.common_attributes["a_bit"])
                    != 0
                ):
                    log.error("PTE has A=1 but is not a Leaf PTE")
                    sys.exit(1)
                elif (
                    BitField.extract_bits(pte_value, self.attributes.common_attributes["d_bit"])
                    != 0
                ):
                    log.error("PTE has D=1 but is not a Leaf PTE")
                    sys.exit(1)

            current_level += 1
            if current_level >= self.get_attribute("num_levels"):
                log.error("Ran out of levels")
                sys.exit(1)
            continue

        pa = a
        pa += BitField.extract_bits(
            va, (self.get_attribute("va_vpn_bits")[current_level][1] - 1, 0)
        )

        log.info(f"Translated PA = {hex(pa)}")
        log.info(f"    PTE value = {hex(pte_value)}")

    def split_mappings_at_page_granularity(self, memory_mappings):
        split_mappings = []
        for entry in memory_mappings:
            if entry.get_field("no_pte_allocation") is True:
                continue

            va = entry.get_field("va")
            pa = entry.get_field("pa")
            for _ in range(entry.get_field("num_pages")):
                new_entry = entry.copy()
                new_entry.set_field("va", va)
                new_entry.set_field("pa", pa)
                new_entry.set_field("num_pages", 1)
                split_mappings.append(new_entry)

                va += entry.get_field("page_size")
                pa += entry.get_field("page_size")

        return split_mappings

    def write_sparse_memory(self, address, value):
        assert (address % self.get_attribute("pte_size_in_bytes")) == 0

        if address in self.pte_memory:
            if self.pte_memory[address] != value:
                log.error(
                    f"[{hex(address)}] already contains a different value {hex(self.pte_memory[address])}. Cannot update to {hex(value)}"
                )
                sys.exit(1)
            log.debug(f"[{hex(address)}] already contains {hex(value)}. No update needed.")
        else:
            self.pte_memory[address] = value
            log.debug(f"[{hex(address)}] = {hex(value)}")

    def read_sparse_memory(self, address):
        assert (address % self.get_attribute("pte_size_in_bytes")) == 0

        if address in self.pte_memory:
            return self.pte_memory[address]
        return None

    # Populates the sparse memory with the pagetable entries
    def create_pagetables_for_mappings(self, memory_mappings):
        for entry in self.split_mappings_at_page_granularity(memory_mappings):
            assert entry.get_field("page_size") in self.get_attribute("page_sizes")
            leaf_level = self.get_attribute("page_sizes").index(entry.get_field("page_size"))
            assert leaf_level < self.get_attribute("num_levels")
            log.debug("\n")
            log.debug(f"Generating PTEs for {entry}")
            log.debug(f"Leaf Level: {leaf_level}")
            current_level = 0

            while current_level <= leaf_level:
                current_level_PT_page = self.get_page(entry.get_field("va"), current_level)

                current_level_range_start = current_level_PT_page.get_page_pa()
                current_level_range_end = current_level_range_start + (PageSize.SIZE_4K)

                pte_value = BitField.place_bits(
                    0, 1, self.attributes.common_attributes["valid_bit"]
                )

                if current_level < leaf_level:
                    next_level_pagetable = self.get_page(entry.get_field("va"), current_level + 1)

                    next_level_range_start = next_level_pagetable.get_page_pa()
                    next_level_range_end = next_level_range_start + (PageSize.SIZE_4K)

                    next_level_pa = next_level_range_start + BitField.extract_bits(
                        entry.get_field("va"), self.get_attribute("va_vpn_bits")[current_level]
                    ) * self.get_attribute("pte_size_in_bytes")

                    assert next_level_pa < next_level_range_end
                else:
                    xwr_bits = entry.get_field("xwr")
                    assert xwr_bits != 0x2 and xwr_bits != 0x6
                    pte_value = BitField.place_bits(
                        pte_value, xwr_bits, self.attributes.common_attributes["xwr_bits"]
                    )

                    if entry.get_field("umode") is not None:
                        pte_value = BitField.place_bits(
                            pte_value,
                            entry.get_field("umode"),
                            self.attributes.common_attributes["umode_bit"],
                        )

                    pte_value = BitField.place_bits(
                        pte_value, 1, self.attributes.common_attributes["a_bit"]
                    )
                    pte_value = BitField.place_bits(
                        pte_value, 1, self.attributes.common_attributes["d_bit"]
                    )

                    if entry.get_field("pbmt_mode") is not None:
                        pbmt_mode = self.attributes.convert_pbmt_mode_string_to_mode(
                            entry.get_field("pbmt_mode")
                        )
                        pte_value = BitField.place_bits(
                            pte_value, pbmt_mode, self.attributes.common_attributes["pbmt_bits"]
                        )

                    pte_value = BitField.place_bits(
                        pte_value,
                        entry.get_field("valid"),
                        self.attributes.common_attributes["valid_bit"],
                    )

                    next_level_pa = entry.get_field("pa")

                for ppn_id in range(len(self.get_attribute("pa_ppn_bits"))):
                    ppn_value = BitField.extract_bits(
                        next_level_pa, self.get_attribute("pa_ppn_bits")[ppn_id]
                    )
                    pte_value = BitField.place_bits(
                        pte_value, ppn_value, self.get_attribute("pte_ppn_bits")[ppn_id]
                    )
                current_level_pt_offset = BitField.extract_bits(
                    entry.get_field("va"), self.get_attribute("va_vpn_bits")[current_level]
                )
                pte_address = (
                    current_level_range_start
                    + current_level_pt_offset * self.get_attribute("pte_size_in_bytes")
                )
                assert pte_address < current_level_range_end
                log.debug(f"PTE address:{hex(pte_address)}, PTE value:{hex(pte_value)}")
                self.write_sparse_memory(pte_address, pte_value)

                current_level += 1

        # Make sure that we have the first and last addresses set so that we
        # know the range of the page table memory when generating the
        # page table section in the assembly file.
        assert self.start_address == self.pages[0].get_page_pa()
        pte_region_sparse_memory_start = self.pages[0].get_page_pa()
        page_size = PageSize.SIZE_4K
        pte_region_sparse_memory_end = (
            self.pages[len(self.pages) - 1].get_page_pa()
            + page_size
            - self.get_attribute("pte_size_in_bytes")
        )

        if pte_region_sparse_memory_start not in self.pte_memory:
            self.pte_memory[pte_region_sparse_memory_start] = 0
        if pte_region_sparse_memory_end not in self.pte_memory:
            self.pte_memory[pte_region_sparse_memory_end] = 0
