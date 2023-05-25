# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

project('JumpStart', 'c',
        default_options : [
          'warning_level=everything',
          'werror=true'
          ]
)

add_project_arguments('-Wno-c++-compat',
                      '-Wno-padded',
                      '-Wno-main',
                      '-mcmodel=medany',
                      language: 'c')

prog_python = find_program('python3')

data_structures_generation_script = meson.current_source_dir() + '/scripts/generate_data_structures.py'
data_strucutures_yaml = get_option('data_structures_yaml')

data_structures_generator_output = custom_target(
                                    'Generate the data structures for build',
                                    input : [data_structures_generation_script, data_strucutures_yaml],
                                    output: ['jumpstart_defines.h', 'jumpstart_data_structures.h', 'thread_attributes.S'],
                                    command: [prog_python,
                                              '@INPUT0@',
                                              '--assembly_file', '@OUTPUT2@',
                                              '--data_structures_file', '@OUTPUT1@',
                                              '--defines_file', '@OUTPUT0@',
                                              '--attributes_yaml', '@INPUT1@',
                                              ])

jumpstart_sources = files('jumpstart_functions.c', 'start.S', 'jumpstart_functions.S')
jumpstart_sources += data_structures_generator_output
jumpstart_includes = include_directories('.')

memory_map_tools_script = meson.current_source_dir() + '/scripts/memory_map_tools.py'
directed_diag_sources = get_option('directed_diag_sources')
directed_diag_memory_map_yaml = get_option('directed_diag_memory_map_yaml')

if directed_diag_memory_map_yaml != '' and directed_diag_sources.length() > 0
  memory_map_tools_output = custom_target(
                                'Generate memory map related source files for build',
                                input : [memory_map_tools_script, directed_diag_memory_map_yaml],
                                output : ['pagetables.S',
                                          'linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--memory_map', '@INPUT1@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  pagetable_s = memory_map_tools_output[0]
  linker_script = memory_map_tools_output[1].full_path()

  directed_diag_sources = [pagetable_s, directed_diag_sources]

  directed_diag_exe = executable('directed_diag',
                        sources: [jumpstart_sources, directed_diag_sources],
                        include_directories: jumpstart_includes,
                        link_args: ['-T' + linker_script, '-nostdlib'])
endif

subdir('tests')
