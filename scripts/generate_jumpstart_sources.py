#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the jumpstart source files from the jumpstart attributes YAML file.

import argparse
import logging as log
import os
import sys
from enum import Enum

import yaml
from utils.lib import DictUtils, ListUtils

priv_modes_enabled = None


class MemoryOp(Enum):
    LOAD = (1,)
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


field_type_to_size_in_bytes = {
    "uint8_t": 1,
    "uint16_t": 2,
    "uint32_t": 4,
    "uint64_t": 8,
}


def generate_getter_and_setter_methods_for_field(
    attributes_data,
    defines_file_fd,
    assembly_file_fd,
    c_struct,
    field_name,
    field_size_in_bytes,
    field_offset_in_struct,
):
    defines_file_fd.write(
        f"#define {c_struct.upper()}_{field_name.upper()}_OFFSET {field_offset_in_struct}\n"
    )

    defines_file_fd.write(
        f"#define GET_{c_struct.upper()}_{field_name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.LOAD, field_size_in_bytes)}   dest_reg, {c_struct.upper()}_{field_name.upper()}_OFFSET(tp);\n"
    )
    defines_file_fd.write(
        f"#define SET_{c_struct.upper()}_{field_name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.STORE, field_size_in_bytes)}   dest_reg, {c_struct.upper()}_{field_name.upper()}_OFFSET(tp);\n\n"
    )

    modes = ListUtils.intersection(["smode", "mmode"], priv_modes_enabled)
    for mode in modes:
        assembly_file_fd.write(f'.section .jumpstart.text.{mode}, "ax"\n')
        getter_method = f"get_{c_struct}_{field_name}_from_{mode}"
        assembly_file_fd.write(f".global {getter_method}\n")
        assembly_file_fd.write(f"{getter_method}:\n")
        assembly_file_fd.write(f"    GET_{c_struct.upper()}_{field_name.upper()}(a0)\n")
        assembly_file_fd.write("    ret\n\n")

        assembly_file_fd.write(f".global set_{c_struct}_{field_name}_from_{mode}\n")
        assembly_file_fd.write(f"set_{c_struct}_{field_name}_from_{mode}:\n")
        assembly_file_fd.write(f"    SET_{c_struct.upper()}_{field_name.upper()}(a0)\n")
        assembly_file_fd.write("    ret\n\n")


def generate_thread_attributes_setup_code(attributes_data, assembly_file_fd):
    modes = ListUtils.intersection(["smode", "mmode"], priv_modes_enabled)
    mode_encodings = {"smode": "PRV_S", "mmode": "PRV_M"}
    for mode in modes:
        assembly_file_fd.write(f'.section .jumpstart.text.{mode}, "ax"\n')
        assembly_file_fd.write("# Inputs:\n")
        assembly_file_fd.write("#   a0: hart id\n")
        assembly_file_fd.write(f".global setup_thread_attributes_from_{mode}\n")
        assembly_file_fd.write(f"setup_thread_attributes_from_{mode}:\n")
        assembly_file_fd.write("  li t1, MAX_NUM_HARTS_SUPPORTED\n")
        assembly_file_fd.write(f"  bgeu a0, t1, jumpstart_{mode}_fail\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  li  t2, THREAD_ATTRIBUTES_STRUCT_SIZE_IN_BYTES\n")
        assembly_file_fd.write("  mul t2, a0, t2\n")
        assembly_file_fd.write("  la  t1, thread_attributes_region\n")
        assembly_file_fd.write("  add tp, t1, t2\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  SET_THREAD_ATTRIBUTES_HART_ID(a0)\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  li t0, TRAP_OVERRIDE_ATTRIBUTES_STRUCT_SIZE_IN_BYTES\n")
        assembly_file_fd.write("  mul t0, a0, t0\n")
        assembly_file_fd.write("  la t1, trap_override_attributes_region\n")
        assembly_file_fd.write("  add t0, t1, t0\n")
        assembly_file_fd.write("  SET_THREAD_ATTRIBUTES_TRAP_OVERRIDE_STRUCT_ADDRESS(t0)\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  li t0, REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES\n")
        assembly_file_fd.write("  mul t0, a0, t0\n")
        assembly_file_fd.write("\n")
        if "mmode" in modes:
            assembly_file_fd.write("  la t1, mmode_reg_context_save_region\n")
            assembly_file_fd.write("  add t1, t1, t0\n")
            assembly_file_fd.write("  la t2, mmode_reg_context_save_region_end\n")
            assembly_file_fd.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
            assembly_file_fd.write(
                "  SET_THREAD_ATTRIBUTES_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
            )
            assembly_file_fd.write("\n")
            assembly_file_fd.write("  la t1, lower_mode_in_mmode_reg_context_save_region\n")
            assembly_file_fd.write("  add t1, t1, t0\n")
            assembly_file_fd.write("  la t2, lower_mode_in_mmode_reg_context_save_region_end\n")
            assembly_file_fd.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
            assembly_file_fd.write(
                "  SET_THREAD_ATTRIBUTES_LOWER_MODE_IN_MMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
            )
            assembly_file_fd.write("\n")
        assembly_file_fd.write("  la t1, smode_reg_context_save_region\n")
        assembly_file_fd.write("  add t1, t1, t0\n")
        assembly_file_fd.write("  la t2, smode_reg_context_save_region_end\n")
        assembly_file_fd.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
        assembly_file_fd.write(
            "  SET_THREAD_ATTRIBUTES_SMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
        )
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  la t1, umode_reg_context_save_region\n")
        assembly_file_fd.write("  add t1, t1, t0\n")
        assembly_file_fd.write("  la t2, umode_reg_context_save_region_end\n")
        assembly_file_fd.write(f"  bgeu t1, t2, jumpstart_{mode}_fail\n")
        assembly_file_fd.write(
            "  SET_THREAD_ATTRIBUTES_UMODE_REG_CONTEXT_SAVE_REGION_ADDRESS(t1)\n"
        )
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  li  t0, 0\n")
        assembly_file_fd.write("  SET_THREAD_ATTRIBUTES_SMODE_SETUP_DONE(t0)\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write(f"  li  t0, {mode_encodings[mode]}\n")
        assembly_file_fd.write("  SET_THREAD_ATTRIBUTES_CURRENT_MODE(t0)\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  li  t0, THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE\n")
        assembly_file_fd.write("  SET_THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER(t0)\n")
        assembly_file_fd.write("\n")
        assembly_file_fd.write("  ret\n")


def generate_reg_context_save_restore_code(attributes_data, defines_file_fd, assembly_file_fd):
    assert (
        attributes_data["reg_context_to_save_across_modes"]["temp_register"]
        not in attributes_data["reg_context_to_save_across_modes"]["registers"]["gprs"]
    )

    num_registers = 0
    for reg_type in attributes_data["reg_context_to_save_across_modes"]["registers"]:
        reg_names = attributes_data["reg_context_to_save_across_modes"]["registers"][reg_type]
        for reg_name in reg_names:
            defines_file_fd.write(
                f"#define {reg_name.upper()}_OFFSET_IN_SAVE_REGION ({num_registers} * 8)\n"
            )
            num_registers += 1

    temp_reg_name = attributes_data["reg_context_to_save_across_modes"]["temp_register"]

    defines_file_fd.write(
        f"\n#define REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES ({num_registers} * 8)\n"
    )

    defines_file_fd.write("\n#define SAVE_ALL_GPRS   ;")
    for gpr_name in attributes_data["reg_context_to_save_across_modes"]["registers"]["gprs"]:
        defines_file_fd.write(
            f"\\\n  sd {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;"
        )
    defines_file_fd.write("\n\n")

    defines_file_fd.write("\n#define RESTORE_ALL_GPRS   ;")
    for gpr_name in attributes_data["reg_context_to_save_across_modes"]["registers"]["gprs"]:
        defines_file_fd.write(
            f"\\\n  ld {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;"
        )
    defines_file_fd.write("\n\n")

    assembly_file_fd.write('\n\n.section .jumpstart.data.smode, "aw"\n')
    modes = ListUtils.intersection(["mmode", "smode", "umode"], priv_modes_enabled)
    if "mmode" in modes:
        modes += ["lower_mode_in_mmode"]
    assembly_file_fd.write(
        f"\n# {modes} context saved registers: \n# {attributes_data['reg_context_to_save_across_modes']['registers']}\n"
    )
    for mode in modes:
        assembly_file_fd.write(f".global {mode}_reg_context_save_region\n")
        assembly_file_fd.write(f"{mode}_reg_context_save_region:\n")
        for i in range(attributes_data["max_num_harts_supported"]):
            assembly_file_fd.write(f"  # save area for hart {i}'s {num_registers} registers\n")
            assembly_file_fd.write(f"  .zero {num_registers * 8}\n\n")
        assembly_file_fd.write(f".global {mode}_reg_context_save_region_end\n")
        assembly_file_fd.write(f"{mode}_reg_context_save_region_end:\n\n")


def generate_jumpstart_sources(
    jumpstart_source_attributes_yaml,
    override_jumpstart_source_attributes,
    defines_file,
    data_structures_file,
    assembly_file,
):
    log.debug(f"Generating jumpstart source files from {jumpstart_source_attributes_yaml}")

    attributes_data = None
    with open(jumpstart_source_attributes_yaml) as f:
        attributes_data = yaml.safe_load(f)
        f.close()

    if override_jumpstart_source_attributes:
        # Override the default jumpstart source attribute values with the values
        # specified on the command line.
        DictUtils.override_dict(
            attributes_data,
            DictUtils.create_dict(override_jumpstart_source_attributes),
        )

    defines_file_fd = open(defines_file, "w")
    data_structures_file_fd = open(data_structures_file, "w")
    assembly_file_fd = open(assembly_file, "w")

    defines_file_fd.write(
        f"// This file is generated by {os.path.basename(__file__)}. Do not edit.\n\n"
    )
    defines_file_fd.write("#pragma once\n\n")
    data_structures_file_fd.write(
        f"// This file is generated by {os.path.basename(__file__)}. Do not edit.\n\n"
    )
    data_structures_file_fd.write("#pragma once\n\n")

    assembly_file_fd.write(
        f"// This file is generated by {os.path.basename(__file__)}. Do not edit.\n\n"
    )
    assembly_file_fd.write('#include "jumpstart_defines.h"\n\n')
    assembly_file_fd.write('#include "cpu_bits.h"\n\n')

    defines_file_fd.write(
        f"#define MAX_NUM_HARTS_SUPPORTED {attributes_data['max_num_harts_supported']}\n\n"
    )

    data_structures_file_fd.write("#include <inttypes.h>\n\n")

    total_size_of_c_structs = 0

    for c_struct in attributes_data["c_structs"]:
        c_struct_fields = attributes_data["c_structs"][c_struct]["fields"]
        current_offset = 0

        data_structures_file_fd.write(f"struct {c_struct} {{\n")
        for field_name in c_struct_fields:
            num_field_elements = 1
            if len(c_struct_fields[field_name].split(",")) > 1:
                field_type = c_struct_fields[field_name].split(",")[0]
                num_field_elements = int(c_struct_fields[field_name].split(",")[1])
                defines_file_fd.write(f"#define NUM_{field_name.upper()} {num_field_elements}\n")
            else:
                field_type = c_struct_fields[field_name]

            field_size_in_bytes = field_type_to_size_in_bytes[field_type]
            if num_field_elements > 1:
                data_structures_file_fd.write(
                    f"    {field_type} {field_name}[{num_field_elements}];\n"
                )
            else:
                data_structures_file_fd.write(f"    {field_type} {field_name};\n")

            # Take care of the padding that the compiler will add.
            while (current_offset % field_size_in_bytes) != 0:
                current_offset += 1

            if c_struct == "thread_attributes":
                generate_getter_and_setter_methods_for_field(
                    attributes_data,
                    defines_file_fd,
                    assembly_file_fd,
                    c_struct,
                    field_name,
                    field_size_in_bytes,
                    current_offset,
                )

            current_offset += field_size_in_bytes * num_field_elements

        data_structures_file_fd.write("};\n\n")

        # Align the end of the struct to 8 bytes.
        while (current_offset % 8) != 0:
            current_offset += 1
        defines_file_fd.write(
            f"#define {c_struct.upper()}_STRUCT_SIZE_IN_BYTES {current_offset}\n\n"
        )

        assembly_file_fd.write('.section .jumpstart.c_structs.smode, "aw"\n\n')
        assembly_file_fd.write(f".global {c_struct}_region\n")
        assembly_file_fd.write(f"{c_struct}_region:\n")
        for i in range(attributes_data["max_num_harts_supported"]):
            assembly_file_fd.write(f".global {c_struct}_region_hart_{i}\n")
            assembly_file_fd.write(f"{c_struct}_region_hart_{i}:\n")
            assembly_file_fd.write(f"  .zero {current_offset}\n")
        assembly_file_fd.write(f".global {c_struct}_region_end\n")
        assembly_file_fd.write(f"{c_struct}_region_end:\n\n")

        total_size_of_c_structs += current_offset

    max_allowed_size_of_c_structs = (
        attributes_data["jumpstart_smode"]["c_structs"]["num_pages"]
        * attributes_data["jumpstart_smode"]["c_structs"]["page_size"]
    )

    if (
        total_size_of_c_structs * attributes_data["max_num_harts_supported"]
        > max_allowed_size_of_c_structs
    ):
        log.error(
            f"Total size of C structs ({total_size_of_c_structs}) exceeds maximum size allocated for C structs {max_allowed_size_of_c_structs}"
        )
        sys.exit(1)

    stack_types = ["smode", "umode"]
    for stack_type in stack_types:
        # Make sure we can equally distribute the number of total stack pages
        # among the harts.
        assert (
            attributes_data[f"jumpstart_{stack_type}"]["stack"]["num_pages"]
            % attributes_data["max_num_harts_supported"]
            == 0
        )
        num_pages_per_hart_for_stack = int(
            attributes_data[f"jumpstart_{stack_type}"]["stack"]["num_pages"]
            / attributes_data["max_num_harts_supported"]
        )
        stack_page_size = attributes_data[f"jumpstart_{stack_type}"]["stack"]["page_size"]

        defines_file_fd.write(
            f"#define NUM_PAGES_PER_HART_FOR_{stack_type.upper()}_STACK {num_pages_per_hart_for_stack}\n\n"
        )

        defines_file_fd.write(f"#define {stack_type.upper()}_STACK_PAGE_SIZE {stack_page_size}\n\n")

        assembly_file_fd.write(f'.section .jumpstart.stack.{stack_type}, "aw"\n')
        assembly_file_fd.write(".align 12\n")
        assembly_file_fd.write(f".global {stack_type}_stack_top\n")
        assembly_file_fd.write(f"{stack_type}_stack_top:\n")
        for i in range(attributes_data["max_num_harts_supported"]):
            assembly_file_fd.write(f".global {stack_type}_stack_top_hart_{i}\n")
            assembly_file_fd.write(f"{stack_type}_stack_top_hart_{i}:\n")
            assembly_file_fd.write(f"  .zero {num_pages_per_hart_for_stack * stack_page_size}\n")
        assembly_file_fd.write(f".global {stack_type}_stack_bottom\n")
        assembly_file_fd.write(f"{stack_type}_stack_bottom:\n\n")

    for define_name in attributes_data["defines"]:
        defines_file_fd.write(f"#define {define_name} {attributes_data['defines'][define_name]}\n")

    generate_reg_context_save_restore_code(attributes_data, defines_file_fd, assembly_file_fd)

    generate_thread_attributes_setup_code(attributes_data, assembly_file_fd)

    defines_file_fd.write("\n")
    current_syscall_number = 0
    for syscall_name in attributes_data["syscall_numbers"]:
        defines_file_fd.write(f"#define {syscall_name} {current_syscall_number}\n")
        current_syscall_number += 1

    defines_file_fd.close()
    data_structures_file_fd.close()
    assembly_file_fd.close()


def main():
    global priv_modes_enabled

    parser = argparse.ArgumentParser(description=__doc__)
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
        "--priv_modes_enabled",
        help=".",
        required=True,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--defines_file", help="Header file containing the defines.", required=True, type=str
    )
    parser.add_argument(
        "--data_structures_file",
        help="Header file containing the c structures.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--assembly_file", help="Assembly file containing functions.", required=True, type=str
    )
    parser.add_argument(
        "-v", "--verbose", help="Verbose output.", action="store_true", default=False
    )
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.DEBUG)
    else:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.INFO)

    priv_modes_enabled = args.priv_modes_enabled

    generate_jumpstart_sources(
        args.jumpstart_source_attributes_yaml,
        args.override_jumpstart_source_attributes,
        args.defines_file,
        args.data_structures_file,
        args.assembly_file,
    )


if __name__ == "__main__":
    main()
