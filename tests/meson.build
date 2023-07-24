# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

fs = import('fs')

jumpstart_tests = [
  ['test000', 'Enable MMU (SATP.mode = sv39), switch to supervisor mode and exit.'],
  ['test001', 'Enable MMU (SATP.mode = sv48), switch to supervisor mode and exit.'],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.'],
  ['test004', 'HWP AMPM perf diag.'],
  ['test005', '16K data block move from WB to UC (PBMT) region.'],
  ['test006', 'Read and Write CSRs.'],
  ['test007', 'UART test.'],
  ['test008', 'IMSIC test.'],
  ['test009', 'Jump to main() in machine mode and exit.'],
  ['test010', 'Override default M-mode start address.'],
]

spike = find_program('spike', required : true)

foreach jumpstart_test : jumpstart_tests
  test_name = jumpstart_test.get(0)
  test_description = jumpstart_test.get(1)

  spike_additional_arguments = jumpstart_test.get(2, '')

  memory_map_file = meson.current_source_dir() + '/' + test_name +'.memory_map.yaml'

  memory_map_tools_output = custom_target(
                                'Generate memory map build files for ' + test_name,
                                input : [memory_map_tools_script, memory_map_file, data_strucutures_yaml],
                                output : [test_name + '.memory_attributes.S',
                                          test_name + '.linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--memory_map', '@INPUT1@',
                                          '--attributes_yaml', '@INPUT2@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  pagetable_s = memory_map_tools_output[0]
  linker_script = memory_map_tools_output[1].full_path()

  test_sources = [pagetable_s]

  if fs.is_file(meson.current_source_dir() + '/' + test_name +'.c')
    test_sources += [test_name + '.c']
  endif

  if fs.is_file(meson.current_source_dir() + '/' + test_name +'.S')
    test_sources += [test_name + '.S']
  endif

  test_exe = executable(test_name,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  spike_args = ['--pass-fail', '--isa=' + get_option('spike_default_isa_string') ]
  if get_option('generate_spike_trace') == true
    spike_args += ['-v1', '--log-commits']
  endif

  if spike_additional_arguments != ''
    spike_args += spike_additional_arguments.split()
  endif

  test(test_name, spike, args : [spike_args, test_exe], suite:'basic')

endforeach
