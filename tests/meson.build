# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

fs = import('fs')

jumpstart_tests = [
  # Specify --isa=rv64gc to the diags that will boot at 0x80000000
  # The default Sentinel behavior is to start at 0x7f800000.
  ['Enable MMU (SATP.mode = sv39), switch to supervisor mode and exit.', 'test000'],
  ['Enable MMU (SATP.mode = sv48), switch to supervisor mode and exit.', 'test001'],
  ['Ping pong between Supervisor and User mode.', 'test002'],
  ['Register and run Supervisor mode illegal instruction exception handler.', 'test003'],
  ['HWP AMPM perf diag.', 'test004'],
  ['Boot at 0x8000_0000. 16K data block move from WB to UC (PBMT) region at 0x42000000.', 'test005', '--isa=RV64GCHV_Zba_Zbb_Zbc_Zbs_Zbkb_Sstc_Svpbmt_Svinval_Sscofpmf_Zicbom_Zicbop_Zicboz_Zfh_Zkt_Zkr_Zicsr_Zifencei_Zawrs_Zicond_Xrivostime -m0x42000000:0x4000,0x80000000:0x4000,0x88000000:0xe000,0x800a0000:0x1000,0x800a0000:0x1001000'],
  ['UART test.', 'test007'],
]

spike = find_program('spike', required : true)

foreach jumpstart_test : jumpstart_tests
  test_description = jumpstart_test[0]
  test_name = jumpstart_test[1]

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
                        link_args: ['-T' + linker_script, '-nostdlib'])

  spike_args = ['--pass-fail', '--isa=' + get_option('spike_default_isa_string') ]
  if get_option('generate_spike_trace') == true
    spike_args += ['-v1', '--log-commits']
  endif

  if spike_additional_arguments != ''
    spike_args += spike_additional_arguments.split()
  endif

  test(test_description, spike, args : [spike_args, test_exe])

endforeach
