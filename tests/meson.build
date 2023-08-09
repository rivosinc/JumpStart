# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

fs = import('fs')

jumpstart_tests = [
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.'],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.'],
  ['test002', 'Run C/Assembly functions in user mode and return to supervisor mode.'],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.'],
  ['test004', 'HWP AMPM perf diag.'],
  ['test005', '16K data block move from WB to UC (PBMT) region.'],
  ['test006', 'Read and Write CSRs.'],
  ['test007', 'UART test.'],
  ['test008', 'IMSIC test.'],
  ['test009', 'Jump to main() in machine mode and exit.'],
  ['test010', 'Override default M-mode start address.'],
  ['test011', 'Handle user mode exceptions in supervisor mode.'],
  ['test012', 'Exit with DIAG_FAILED to test fail path.', '', true],
  ['test013', 'test000 with 4 harts.', '-p4'],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', '-p3', true],
  ['test015', 'MP IMSIC test.', '-p4'],
]

foreach jumpstart_test : jumpstart_tests
  test_prefix = jumpstart_test.get(0)
  test_description = jumpstart_test.get(1)

  spike_additional_arguments = jumpstart_test.get(2, '')

  test_should_fail = jumpstart_test.get(3, false)

  diag_attributes_yaml = files(test_prefix +'.diag_attributes.yaml')

  diag_source_generator_output = custom_target(
                                'Generate diag attribute build files for ' + test_prefix,
                                input : [diag_source_generator,
                                          diag_attributes_yaml,
                                          jumpstart_source_attributes_yaml],
                                output : [test_prefix + '.generated.S',
                                          test_prefix + '.linker_script.ld'],
                                command : [prog_python,
                                          '@INPUT0@',
                                          '--diag_attributes_yaml', '@INPUT1@',
                                          '--jumpstart_source_attributes_yaml', '@INPUT2@',
                                          '--output_assembly_file', '@OUTPUT0@',
                                          '--output_linker_script', '@OUTPUT1@',
                                          ])

  test_sources = [diag_source_generator_output[0]]
  linker_script = diag_source_generator_output[1].full_path()

  possible_suffixes = ['_umode.S', '_umode.c', '.S', '.c']
  foreach possible_suffix : possible_suffixes
    if fs.is_file(meson.current_source_dir() + '/' + test_prefix + possible_suffix)
      test_sources += [test_prefix + possible_suffix]
    endif
  endforeach

  test_exe = executable(test_prefix,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  spike_args = default_spike_args

  if spike_additional_arguments != ''
    spike_args += spike_additional_arguments.split()
  endif

  test(test_prefix + ' 🧪 ' + test_description,
        spike,
        args : [spike_args, test_exe],
        suite:'basic',
        should_fail: test_should_fail)

endforeach
