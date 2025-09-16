# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

start_in_mmode_tests = [] # diag main() is in mmode
start_in_smode_tests = [] # diag main() is in smode

tests_disabled_on_spike = []

subdir('common')
test_root_directories = [meson.current_source_dir() + '/' + 'common']

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
  test_root_directories += [meson.current_source_dir() + '/' + 'rivos_internal']
endif

unit_tests = []
start_in_mmode_tests + start_in_smode_tests

if 'mmode' in riscv_priv_modes_enabled
  unit_tests += start_in_mmode_tests
endif
if 'smode' in riscv_priv_modes_enabled
  unit_tests += start_in_smode_tests
endif


foreach unit_test : unit_tests
  test_name = unit_test.get(0)
  test_description = unit_test.get(1)

  spike_additional_arguments = unit_test.get(2, '')

  test_expected_to_fail = unit_test.get(3, false)

  test_disabled_on_spike = test_name in tests_disabled_on_spike

  if get_option('run_target') == 'spike' and test_disabled_on_spike == true
    continue
  endif

  test_sources = []
  foreach test_root_dir : test_root_directories
    foreach suffix : source_suffixes
      if fs.is_file(test_root_dir + '/' + test_name + '/' + test_name + suffix)
        test_sources += files(test_root_dir + '/' + test_name + '/' + test_name + suffix)
      endif
    endforeach

    if fs.is_file(test_root_dir + '/' + test_name + '/' + test_name + '.diag_attributes.yaml')
      diag_attributes_yaml = files(test_root_dir + '/' + test_name + '/' + test_name + '.diag_attributes.yaml')
      break
    endif
  endforeach

  test_defines_file_name = test_name + '.defines.h'
  diag_source_generator_output = custom_target(
                                'Generate diag attributes related source files for ' + test_name,
                                input : diag_source_generator_common_inputs + [diag_attributes_yaml],
                                output : [test_name + '.generated.S',
                                          test_name + '.linker_script.ld',
                                          test_name + '.defines.h',
                                          test_name + '.data_structures.h',
                                          ],
                                command : diag_source_generator_command)

  test_sources += diag_source_generator_output[0]
  linker_script = diag_source_generator_output[1]
  test_defines = diag_source_generator_output[2]
  test_data_structures = diag_source_generator_output[3]

  test_exe = executable(test_name,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args + ['-include', test_defines.full_path(), '-include', test_data_structures.full_path()],
                        link_args: ['-T' + linker_script.full_path()],
                        link_depends: linker_script,
                        dependencies: declare_dependency(sources: test_defines)
                        )

  if get_option('diag_generate_disassembly') == true
    custom_target(test_name + '_dump',
                capture          : true,
                output           : test_name + '.dis',
                build_by_default : true,
                command          : [objdump, '-D', '-S', '-t', test_exe],
                depends          : [test_exe])
  endif

  if get_option('run_target') == 'spike'
    spike_args = default_spike_args

    if spike_additional_arguments != ''
      spike_args += spike_additional_arguments.split()
    endif

    target = spike
    args = [spike_args, test_exe]
    timeout = get_option('spike_timeout')
    should_fail = test_expected_to_fail

    test(test_name + ' 🧪 ' + test_description,
          target,
          args : args,
          timeout: timeout,
          suite:'basic',
          depends: test_exe,
          should_fail: should_fail)
  endif

endforeach
