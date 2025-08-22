# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import sys

from .memory_mapping import MemoryMapping
from .page_size import PageSize
from .page_tables import TranslationStage


class LinkerScriptSection:
    def __init__(self, entry):
        if entry.get_field("translation_stage") is None:
            raise ValueError(f"Entry does not have a translation stage: {entry}")
        stage = entry.get_field("translation_stage")

        if entry.get_field(TranslationStage.get_translates_to(stage)) is None:
            raise ValueError(
                f"Entry does not have a valid destination address for the {stage} stage: {entry}"
            )

        # Get VA as linker script is supposed to use Virtual address. For M-mode and R-code mappings
        # fallback to PA as these don't have a virtual address.
        self.virt_start_address = entry.get_field(TranslationStage.get_translates_from(stage))
        self.phys_start_address = entry.get_field(TranslationStage.get_translates_to(stage))
        if self.virt_start_address is None:
            self.virt_start_address = self.phys_start_address

        if entry.get_field("num_pages") is None:
            raise ValueError(f"Entry does not have a number of pages: {entry}")
        if entry.get_field("page_size") is None:
            raise ValueError(f"Entry does not have a page size: {entry}")

        self.size = entry.get_field("num_pages") * entry.get_field("page_size")

        if entry.get_field("linker_script_section") is None:
            raise ValueError(f"Entry does not have a linker script section: {entry}")

        # If this is a list of sections, the first section listed is the
        # top level section that all the other sections get placed in.
        subsections = entry.get_field("linker_script_section").split(",")
        self.top_level_name = subsections[0]

        # main() automatically gets placed in the .text.startup section
        # and we want the .text.startup section to be part of the
        # .text section.
        if ".text" in subsections and ".text.startup" not in subsections:
            # Place .text.startup at the beginning of the list
            # so that main() is the first thing in the .text section?
            subsections.insert(0, ".text.startup")

        self.type = ""
        self.padded = False
        if ".bss" in subsections:
            # Switching BSS from the default NOBITS to PROGBITS.
            # With NOBITS the BSS section doesn't take up space in the
            # ELF file and the loader or runtime is expected to
            # zero out the memory region. This is fine for a real
            # system but the diag may be loaded into an environment
            # where the loader doesn't zero out the memory region.
            # We would have to run a memset() to zero out the BSS which
            # will unnecessarily consume simulation time.
            # PROGBITS ensures that the BSS section is assigned space
            # in the ELF file and initialized with zeros.
            # [Slack] https://rivosinc.slack.com/archives/C030C5A4BUZ/p1710990976820719?thread_ts=1710960882.327799&cid=C030C5A4BUZ
            self.type = "(TYPE=SHT_PROGBITS)"
            self.padded = True

        self.subsections = subsections

    def get_top_level_name(self):
        return self.top_level_name

    def get_virt_start_address(self):
        return self.virt_start_address

    def get_virt_end_address(self):
        return self.virt_start_address + self.size

    def get_phys_start_address(self):
        return self.phys_start_address

    def get_phys_end_address(self):
        return self.phys_start_address + self.size

    def get_size(self):
        return self.size

    def get_type(self):
        return self.type

    def get_subsections(self):
        return self.subsections

    def is_padded(self):
        return self.padded

    def merge(self, other_section):
        # Add all the missing subsections from the other section to this section
        for subsection in other_section.get_subsections():
            if subsection not in self.subsections:
                self.subsections.append(subsection)

        if self.get_phys_start_address() > other_section.get_phys_start_address():
            self.phys_start_address = other_section.get_phys_start_address()

        if self.get_phys_end_address() < other_section.get_phys_end_address():
            self.size = other_section.get_phys_end_address() - self.get_phys_start_address()

        if other_section.is_padded():
            self.padded = True

        if other_section.get_type() != "":
            self.type = other_section.get_type()

    def __str__(self):
        return f"Section: {self.get_top_level_name()}; Start Address: {hex(self.get_phys_start_address())}; Size: {self.get_size()}; Subsections: {self.get_subsections()}; Type: {self.get_type()}; Padded: {self.is_padded()}"


class LinkerScript:
    def __init__(self, entry_label, elf_address_range, mappings, attributes_file):
        self.entry_label = entry_label
        self.attributes_file = attributes_file
        self.elf_start_address, self.elf_end_address = elf_address_range

        self.guard_sections = None

        mappings_with_linker_sections = []
        for stage in TranslationStage.get_enabled_stages():
            mappings_with_linker_sections.extend(
                [
                    entry
                    for entry in mappings[stage]
                    if entry.get_field("linker_script_section") is not None
                ]
            )

        self.sections = []
        for entry in mappings_with_linker_sections:
            new_section = LinkerScriptSection(entry)

            existing_sections_with_matching_subsections = self.find_sections_with_subsections(
                new_section.get_subsections()
            )

            if len(existing_sections_with_matching_subsections) == 0:
                self.sections.append(new_section)
            elif len(existing_sections_with_matching_subsections) == 1:
                log.debug(
                    f"Merging linker sections\n\t{existing_sections_with_matching_subsections[0]}\n\t{new_section}"
                )
                existing_sections_with_matching_subsections[0].merge(new_section)
            else:
                raise ValueError(
                    f"Section names in {new_section} are used in {len(existing_sections_with_matching_subsections)} other sections."
                )

        self.sections.sort(key=lambda x: x.get_phys_start_address())

        # Add guard sections after each section that isn't immediately followed
        # by another section.
        # The linker can detect overruns of a section if there is a section
        # immediately following it in the memory layout.
        # We will also need to generate the corresponding assembly code
        # for each guard section. Otherwise the linker will ignore the guard section.
        self.guard_sections = []
        for i in range(len(self.sections) - 1):
            if (
                self.sections[i].get_phys_end_address()
                < self.sections[i + 1].get_phys_start_address()
            ):
                self.guard_sections.append(
                    LinkerScriptSection(
                        MemoryMapping(
                            {
                                "translation_stage": TranslationStage.get_enabled_stages()[
                                    0
                                ],  # any stage works. We just need a valid one.
                                TranslationStage.get_translates_to(
                                    TranslationStage.get_enabled_stages()[0]
                                ): self.sections[i].get_phys_end_address(),
                                "num_pages": 1,
                                "page_size": PageSize.SIZE_4K,
                                "linker_script_section": f".linker_guard_section_{len(self.guard_sections)}",
                            }
                        )
                    )
                )
        self.sections.extend(self.guard_sections)
        self.sections.sort(key=lambda x: x.get_phys_start_address())

        # check for overlaps in the sections and that sections are within ELF address range
        for i in range(len(self.sections)):
            section_start = self.sections[i].get_phys_start_address()
            section_end = section_start + self.sections[i].get_size()

            # Check section is within allowed ELF address range if specified
            if self.elf_start_address is not None or self.elf_end_address is not None:
                if self.elf_start_address is not None and section_start < self.elf_start_address:
                    raise ValueError(
                        f"{self.sections[i]} is outside allowed ELF address range - start address {hex(section_start)} is less than elf_start_address {hex(self.elf_start_address)}"
                    )
                if self.elf_end_address is not None and section_end > self.elf_end_address:
                    raise ValueError(
                        f"{self.sections[i]} is outside allowed ELF address range - end address {hex(section_end)} is greater than elf_end_address {hex(self.elf_end_address)}"
                    )

            # Check for overlap with next section
            if i < len(self.sections) - 1:
                if section_end > self.sections[i + 1].get_phys_start_address():
                    raise ValueError(
                        f"Linker sections overlap:\n\t{self.sections[i]}\n\t{self.sections[i + 1]}"
                    )

        self.program_headers = []
        for section in self.sections:
            self.program_headers.append(section.get_top_level_name())

        self.discard_sections = [".note", ".comment", ".eh_frame", ".eh_frame_hdr"]

    def find_sections_with_subsections(self, subsection_names):
        matching_sections = []
        for section in self.sections:
            if set(subsection_names).issubset(set(section.get_subsections())):
                matching_sections.append(section)
        return matching_sections

    def get_sections(self):
        return self.sections

    def get_program_headers(self):
        return self.program_headers

    def get_discard_sections(self):
        return self.discard_sections

    def get_entry_label(self):
        return self.entry_label

    def get_attributes_file(self):
        return self.attributes_file

    def get_guard_sections(self):
        return self.guard_sections

    def generate(self, output_linker_script):
        file = open(output_linker_script, "w")
        if file is None:
            raise Exception(f"Unable to open {output_linker_script} for writing")

        file.write(
            f"/* This file is auto-generated by {sys.argv[0]} from {self.get_attributes_file()} */\n"
        )
        file.write('OUTPUT_ARCH( "riscv" )\n')
        file.write(f"ENTRY({self.get_entry_label()})\n\n")

        # Add MEMORY region definitions
        file.write("MEMORY\n{\n")
        for section in self.get_sections():
            memory_name = section.get_top_level_name().replace(".", "_").upper()
            start_addr = hex(section.get_virt_start_address())
            size = hex(section.get_size())
            file.write(f"    {memory_name} (rwx) : ORIGIN = {start_addr}, LENGTH = {size}\n")
        file.write("}\n\n")

        file.write("SECTIONS\n{\n")
        defined_sections = []

        # The linker script lays out the diag in physical memory. The
        # mappings are already sorted by PA.
        for section in self.get_sections():
            file.write(f"\n\n   /* {','.join(section.get_subsections())}:\n")
            file.write(
                f"       PA Range: {hex(section.get_phys_start_address())} - {hex(section.get_phys_end_address())}\n"
                f"       VA Range: {hex(section.get_virt_start_address())} - {hex(section.get_virt_end_address())}\n"
            )
            file.write("   */\n")
            file.write(f"   . = {hex(section.get_virt_start_address())};\n")

            top_level_section_variable_name_prefix = (
                section.get_top_level_name().replace(".", "_").upper()
            )
            file.write(f"   {top_level_section_variable_name_prefix}_START = .;\n")
            file.write(
                f"   {section.get_top_level_name()} {section.get_type()} :  AT({hex(section.get_phys_start_address())}) {{\n"
            )
            for section_name in section.get_subsections():
                assert section_name not in defined_sections
                file.write(f"      *({section_name})\n")
                defined_sections.append(section_name)
            if section.is_padded():
                file.write("      BYTE(0)\n")
            file.write(
                f"   }} > {top_level_section_variable_name_prefix} : {section.get_top_level_name()}\n"
            )
            file.write(
                f"   . = {hex(section.get_virt_start_address() + section.get_size() - 1)};\n"
            )
            file.write(f"  {top_level_section_variable_name_prefix}_END = .;\n")

        file.write("\n\n/DISCARD/ : { *(" + " ".join(self.get_discard_sections()) + ") }\n")
        file.write("\n}\n")

        # Specify separate load segments in the program headers for the
        # different sections.
        # Without this, GCC would split out the sections into separate
        # load segments but LLVM would put non-adjacent sections with
        # identical attributes into the same load segment.
        # This would cause the loader to load gaps between the sections
        # as well which spike has issues with as it doesn't treat
        # the entire memory range as valid.
        # Reference:
        # https://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_node/ld_23.html
        # https://rivosinc.slack.com/archives/C030C5A4BUZ/p1710366517457539
        file.write("\nPHDRS\n{\n")
        for program_header in self.get_program_headers():
            file.write(f"  {program_header} PT_LOAD ;\n")
        file.write("}\n")

        file.close()
