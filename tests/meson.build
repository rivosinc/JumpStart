# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

jumpstart_tests = [
  ['Jump to main, enable MMU, switch to supervisor mode and exit. SATP.mode = sv39', 'test000'],
  ['Jump to main, enable MMU, switch to supervisor mode and exit. SATP.mode = sv48', 'test001'],
]

spike = find_program('spike', required : true)

foreach jumpstart_test : jumpstart_tests
  test_description = jumpstart_test[0]
  test_name = jumpstart_test[1]

  memory_map_file = meson.current_source_dir() + '/' + test_name +'.memory_map.yaml'

  memory_map_tools_output = custom_target(
                                'Generate memory map build files for ' + test_name,
                                input : [memory_map_tools_script, memory_map_file ],
                                output : [test_name + '.pagetables.S',
                                          test_name + '.linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--memory_map', '@INPUT1@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  pagetable_s = memory_map_tools_output[0]
  linker_script = memory_map_tools_output[1].full_path()

  test_sources = [pagetable_s, test_name + '.main.c']

  test_exe = executable(test_name,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  test(test_description, spike, args : ['--pass-fail', test_exe])

endforeach
