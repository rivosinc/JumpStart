#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Rivos Inc.
# SPDX-FileCopyrightText: Copyright (c) 2022 by Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the jumpstart source files from the jumpstart attributes YAML file.

import argparse
from enum import Enum
import logging as log
import os
import sys

import yaml


class MemoryOp(Enum):
    LOAD = 1,
    STORE = 2


def get_memop_of_size(memory_op_type, size_in_bytes):
    if memory_op_type == MemoryOp.LOAD:
        op = 'l'
    elif memory_op_type == MemoryOp.STORE:
        op = 's'
    else:
        raise Exception(f'Invalid memory op type: {memory_op_type}')

    if size_in_bytes == 1:
        return op + 'b'
    elif size_in_bytes == 2:
        return op + 'h'
    elif size_in_bytes == 4:
        return op + 'w'
    elif size_in_bytes == 8:
        return op + 'd'
    else:
        raise Exception(f'Invalid size: {size_in_bytes} bytes')


field_type_to_size_in_bytes = {
    'uint8_t': 1,
    'uint16_t': 2,
    'uint32_t': 4,
    'uint64_t': 8,
}


def generate_getter_and_setter_methods_for_field(defines_file_fd,
                                                 assembly_file_fd, c_struct,
                                                 field_name,
                                                 field_size_in_bytes,
                                                 field_offset_in_struct):
    defines_file_fd.write(
        f"#define {c_struct.upper()}_{field_name.upper()}_OFFSET {field_offset_in_struct}\n"
    )

    defines_file_fd.write(
        f"#define GET_{c_struct.upper()}_{field_name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.LOAD, field_size_in_bytes)}   dest_reg, {c_struct.upper()}_{field_name.upper()}_OFFSET(tp);\n"
    )
    defines_file_fd.write(
        f"#define SET_{c_struct.upper()}_{field_name.upper()}(dest_reg) {get_memop_of_size(MemoryOp.STORE, field_size_in_bytes)}   dest_reg, {c_struct.upper()}_{field_name.upper()}_OFFSET(tp);\n\n"
    )

    modes = ['supervisor', 'machine']
    for mode in modes:
        assembly_file_fd.write(f'.section .jumpstart.text.{mode}, "ax"\n')
        getter_method = f'get_{c_struct}_{field_name}_from_{mode}_mode'
        assembly_file_fd.write(f'.global {getter_method}\n')
        assembly_file_fd.write(f'{getter_method}:\n')
        assembly_file_fd.write(
            f'    GET_{c_struct.upper()}_{field_name.upper()}(a0)\n')
        assembly_file_fd.write(f'    ret\n\n')

        assembly_file_fd.write(
            f'.global set_{c_struct}_{field_name}_from_{mode}_mode\n')
        assembly_file_fd.write(
            f'set_{c_struct}_{field_name}_from_{mode}_mode:\n')
        assembly_file_fd.write(
            f'    SET_{c_struct.upper()}_{field_name.upper()}(a0)\n')
        assembly_file_fd.write(f'    ret\n\n')


def generate_reg_context_save_restore_code(attributes_data, defines_file_fd,
                                           assembly_file_fd):
    assert (
        attributes_data['reg_context_to_save_across_modes']['temp_register']
        not in attributes_data['reg_context_to_save_across_modes']['registers']
        ['gprs'])

    num_registers = 0
    for reg_type in attributes_data['reg_context_to_save_across_modes'][
            'registers']:
        reg_names = attributes_data['reg_context_to_save_across_modes'][
            'registers'][reg_type]
        for reg_name in reg_names:
            defines_file_fd.write(
                f"#define {reg_name.upper()}_OFFSET_IN_SAVE_REGION ({num_registers} * 8)\n"
            )
            num_registers += 1

    temp_reg_name = attributes_data['reg_context_to_save_across_modes'][
        'temp_register']

    defines_file_fd.write(
        f'\n#define REG_CONTEXT_SAVE_REGION_SIZE_IN_BYTES ({num_registers} * 8)\n'
    )

    defines_file_fd.write(f'\n#define SAVE_ALL_GPRS   ;')
    for gpr_name in attributes_data['reg_context_to_save_across_modes'][
            'registers']['gprs']:
        defines_file_fd.write(
            f'\\\n  sd {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;'
        )
    defines_file_fd.write(f'\n\n')

    defines_file_fd.write(f'\n#define RESTORE_ALL_GPRS   ;')
    for gpr_name in attributes_data['reg_context_to_save_across_modes'][
            'registers']['gprs']:
        defines_file_fd.write(
            f'\\\n  ld {gpr_name}, {gpr_name.upper()}_OFFSET_IN_SAVE_REGION({temp_reg_name})   ;'
        )
    defines_file_fd.write(f'\n\n')

    assembly_file_fd.write(f'\n\n.section .jumpstart.data.privileged, "aw"\n')
    modes = ['mmode', 'smode', 'umode']
    assembly_file_fd.write(
        f"\n# {modes} context saved registers: \n# {attributes_data['reg_context_to_save_across_modes']['registers']}\n"
    )
    for mode in modes:
        assembly_file_fd.write(f'.global {mode}_reg_context_save_region\n')
        assembly_file_fd.write(f'{mode}_reg_context_save_region:\n')
        for i in range(attributes_data['max_num_harts_supported']):
            assembly_file_fd.write(
                f"  # save area for hart {i}'s {num_registers} registers\n")
            assembly_file_fd.write(f'  .zero {num_registers * 8}\n\n')
        assembly_file_fd.write(f'.global {mode}_reg_context_save_region_end\n')
        assembly_file_fd.write(f'{mode}_reg_context_save_region_end:\n\n')


def generate_jumpstart_sources(jumpstart_source_attributes_yaml, defines_file,
                               data_structures_file, assembly_file):
    log.debug(
        f'Generating jumpstart source files from {jumpstart_source_attributes_yaml}'
    )

    attributes_data = None
    with open(jumpstart_source_attributes_yaml, "r") as f:
        attributes_data = yaml.safe_load(f)
        f.close()

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

    defines_file_fd.write(
        f"#define MAX_NUM_HARTS_SUPPORTED {attributes_data['max_num_harts_supported']}\n\n"
    )

    data_structures_file_fd.write("#include <inttypes.h>\n\n")

    total_size_of_c_structs = 0

    for c_struct in attributes_data['c_structs']:
        c_struct_fields = attributes_data['c_structs'][c_struct]['fields']
        current_offset = 0

        data_structures_file_fd.write(f"struct {c_struct} {{\n")
        for field_name in c_struct_fields:

            num_field_elements = 1
            if len(c_struct_fields[field_name].split(",")) > 1:
                field_type = c_struct_fields[field_name].split(",")[0]
                num_field_elements = int(
                    c_struct_fields[field_name].split(",")[1])
                defines_file_fd.write(
                    f"#define NUM_{field_name.upper()} {num_field_elements}\n")
            else:
                field_type = c_struct_fields[field_name]

            field_size_in_bytes = field_type_to_size_in_bytes[field_type]
            if num_field_elements > 1:
                data_structures_file_fd.write(
                    f"    {field_type} {field_name}[{num_field_elements}];\n")
            else:
                data_structures_file_fd.write(
                    f"    {field_type} {field_name};\n")

            # Take care of the padding that the compiler will add.
            while (current_offset % field_size_in_bytes) != 0:
                current_offset += 1

            if c_struct == "thread_attributes":
                generate_getter_and_setter_methods_for_field(
                    defines_file_fd, assembly_file_fd, c_struct, field_name,
                    field_size_in_bytes, current_offset)

            current_offset += field_size_in_bytes * num_field_elements

        data_structures_file_fd.write("};\n\n")

        # Align the end of the struct to 8 bytes.
        while (current_offset % 8) != 0:
            current_offset += 1
        defines_file_fd.write(
            f"#define {c_struct.upper()}_STRUCT_SIZE_IN_BYTES {current_offset}\n\n"
        )

        assembly_file_fd.write(
            f'.section .jumpstart.data.privileged, "aw"\n\n')
        assembly_file_fd.write(f'.global {c_struct}_region\n')
        assembly_file_fd.write(f'{c_struct}_region:\n')
        for i in range(attributes_data['max_num_harts_supported']):
            assembly_file_fd.write(f'.global {c_struct}_region_hart_{i}\n')
            assembly_file_fd.write(f'{c_struct}_region_hart_{i}:\n')
            assembly_file_fd.write(f"  .zero {current_offset}\n")
        assembly_file_fd.write(f'.global {c_struct}_region_end\n')
        assembly_file_fd.write(f'{c_struct}_region_end:\n\n')

        total_size_of_c_structs += current_offset

    if total_size_of_c_structs * attributes_data['max_num_harts_supported'] > (
            attributes_data['jumpstart_privileged_data_page_counts']
        ['num_pages_for_c_structs'] * 4096):
        log.error(
            f"Total size of C structs ({total_size_of_c_structs}) exceeds maximum size allocated for C structs {attributes_data['jumpstart_privileged_data_page_counts']['num_pages_for_c_structs'] * 4096}"
        )
        sys.exit(1)

    stack_types = ['privileged', 'umode']
    for stack_type in stack_types:
        # Make sure we can equally distribute the number of total stack pages
        # among the harts.
        assert (attributes_data[f'jumpstart_{stack_type}_data_page_counts']
                ['num_pages_for_stack'] %
                attributes_data['max_num_harts_supported'] == 0)
        num_pages_per_hart_for_stack = int(
            attributes_data[f'jumpstart_{stack_type}_data_page_counts']
            ['num_pages_for_stack'] /
            attributes_data['max_num_harts_supported'])

        defines_file_fd.write(
            f'#define NUM_PAGES_PER_HART_FOR_{stack_type.upper()}_STACK {num_pages_per_hart_for_stack}\n\n'
        )

        assembly_file_fd.write(
            f'.section .jumpstart.data.{stack_type}, "aw"\n')
        assembly_file_fd.write(f'.align 12\n')
        assembly_file_fd.write(f'.global {stack_type}_stack_top\n')
        assembly_file_fd.write(f'{stack_type}_stack_top:\n')
        for i in range(attributes_data['max_num_harts_supported']):
            assembly_file_fd.write(
                f'.global {stack_type}_stack_top_hart_{i}\n')
            assembly_file_fd.write(f'{stack_type}_stack_top_hart_{i}:\n')
            assembly_file_fd.write(
                f"  .zero {num_pages_per_hart_for_stack * 4096}\n")
        assembly_file_fd.write(f'.global {stack_type}_stack_bottom\n')
        assembly_file_fd.write(f'{stack_type}_stack_bottom:\n\n')

    for define_name in attributes_data['defines']:
        defines_file_fd.write(
            f"#define {define_name} {attributes_data['defines'][define_name]}\n"
        )

    generate_reg_context_save_restore_code(attributes_data, defines_file_fd,
                                           assembly_file_fd)

    defines_file_fd.write("\n")
    current_syscall_number = 0
    for syscall_name in attributes_data['syscall_numbers']:
        defines_file_fd.write(
            f"#define {syscall_name} {current_syscall_number}\n")
        current_syscall_number += 1

    defines_file_fd.close()
    data_structures_file_fd.close()
    assembly_file_fd.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jumpstart_source_attributes_yaml',
                        help=f'YAML containing the jumpstart attributes.',
                        required=True,
                        type=str)
    parser.add_argument('--defines_file',
                        help=f'Header file containing the defines.',
                        required=True,
                        type=str)
    parser.add_argument('--data_structures_file',
                        help=f'Header file containing the c structures.',
                        required=True,
                        type=str)
    parser.add_argument('--assembly_file',
                        help=f'Assembly file containing functions.',
                        required=True,
                        type=str)
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

    generate_jumpstart_sources(args.jumpstart_source_attributes_yaml,
                               args.defines_file, args.data_structures_file,
                               args.assembly_file)


if __name__ == '__main__':
    main()
