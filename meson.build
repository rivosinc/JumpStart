# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

project('JumpStart', 'c',
        default_options : [
          'warning_level=everything',
          'werror=true',
          ],
        meson_version: '>=1.1.0'
)

add_project_arguments('-Wno-c++-compat',
                      '-Wno-padded',
                      '-Wno-pedantic',
                      '-mcmodel=medany',
                      language: 'c')

prog_python = find_program('python3')

data_structures_generation_script = meson.current_source_dir() + '/scripts/generate_data_structures.py'
data_structures_yaml = meson.current_source_dir() + '/jumpstart_data_structures.yaml'

data_structures_generator_output = custom_target(
                                    'Generate the data structures for build',
                                    input : [data_structures_generation_script, data_structures_yaml],
                                    output: ['jumpstart_defines.h', 'jumpstart_data_structures.h', 'thread_attributes.S'],
                                    command: [prog_python,
                                              '@INPUT0@',
                                              '--assembly_file', '@OUTPUT2@',
                                              '--data_structures_file', '@OUTPUT1@',
                                              '--defines_file', '@OUTPUT0@',
                                              '--attributes_yaml', '@INPUT1@',
                                              ])

jumpstart_sources = files('jumpstart_functions.c', 'start.S', 'end.S', 'jumpstart_functions.S', 'jumpstart_uart.c', 'jumpstart_imsic.c', 'string.c')
jumpstart_sources += data_structures_generator_output
jumpstart_includes = include_directories('.')

memory_map_tools_script = meson.current_source_dir() + '/scripts/memory_map_tools.py'

diag_sources = get_option('diag_sources')
diag_memory_map_yaml = get_option('diag_memory_map_yaml')

default_c_args_list = ['-march=' + get_option('gcc_march_string')]

if diag_memory_map_yaml != '' and diag_sources.length() > 0
  memory_map_tools_output = custom_target(
                                'Generate memory map related source files for build',
                                input : [memory_map_tools_script, diag_memory_map_yaml, data_structures_yaml],
                                output : ['memory_attributes.S',
                                          'linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--memory_map', '@INPUT1@',
                                          '--attributes_yaml', '@INPUT2@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  pagetable_s = memory_map_tools_output[0]
  linker_script = memory_map_tools_output[1].full_path()

  diag_sources = [pagetable_s, diag_sources]

  diag_name = get_option('diag_name')

  diag_exe = executable(diag_name,
                        sources: [jumpstart_sources, diag_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])
else

  # Don't build the tests if we're building a directed diag.
  subdir('tests')

endif
