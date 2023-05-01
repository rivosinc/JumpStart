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
                      language: 'c')

prog_python = find_program('python3')

memory_map_tools_script = meson.current_source_dir() + '/scripts/memory_map_tools.py'

jumpstart_sources = files('jumpstart_functions.c', 'start.S')
jumpstart_includes = include_directories('.')

directed_diag_main_c = get_option('directed_diag_main_c')
directed_diag_memory_map_yaml = get_option('directed_diag_memory_map_yaml')

if directed_diag_main_c != '' and directed_diag_memory_map_yaml != ''
  memory_map_tools_output = custom_target(
                                'Generate memory map related source files for build',
                                input : [memory_map_tools_script, directed_diag_memory_map_yaml ],
                                output : ['pagetables.s',
                                          'linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--memory_map', '@INPUT1@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  pagetable_s = memory_map_tools_output[0]
  linker_script = memory_map_tools_output[1].full_path()

  directed_diag_sources = [pagetable_s, directed_diag_main_c]

  # TODO: Support getting the SATP mode from the memory map file
  directed_diag_exe = executable('directed_diag',
                        sources: [jumpstart_sources, directed_diag_sources],
                        c_args : '-DSATP_MODE=8',
                        include_directories: jumpstart_includes,
                        link_args: ['-T' + linker_script, '-nostdlib'])
endif

subdir('tests')
