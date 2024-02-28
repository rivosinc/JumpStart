# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

subdir('common')

unit_tests = common_tests
unit_tests_disabled_on_qemu = common_tests_disabled_on_qemu
unit_tests_disabled_on_spike = common_tests_disabled_on_spike

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
  unit_tests += rivos_internal_tests
  unit_tests_disabled_on_qemu += rivos_internal_tests_disabled_on_qemu
  unit_tests_disabled_on_spike += rivos_internal_tests_disabled_on_spike
endif

if get_option('diag_target') == 'qemu'
  diag_source_generator_command += ['--override_diag_attributes=in_qemu_mode=True']
endif


foreach unit_test : unit_tests
  test_name = unit_test.get(0)
  test_description = unit_test.get(1)

  spike_additional_arguments = unit_test.get(2, '')

  test_expected_to_fail = unit_test.get(3, false)

  test_disabled_on_qemu = test_name in unit_tests_disabled_on_qemu
  test_disabled_on_spike = test_name in unit_tests_disabled_on_spike

  if get_option('diag_target') == 'spike' and test_disabled_on_spike == true
    continue
  elif get_option('diag_target') == 'qemu' and test_disabled_on_qemu == true
    continue
  endif

  if fs.is_file(meson.current_source_dir() + '/' + 'common' + '/' + test_name + '.diag_attributes.yaml')
    diag_attributes_yaml = files('common' + '/' + test_name + '.diag_attributes.yaml')
  elif get_option('rivos_internal_build') == true
    if fs.is_file(meson.current_source_dir() + '/' + 'rivos_internal' + '/' + test_name + '.diag_attributes.yaml')
      diag_attributes_yaml = files('rivos_internal' + '/' + test_name + '.diag_attributes.yaml')
    endif
  endif

  diag_source_generator_output = custom_target(
                                'Generate diag attributes related source files for ' + test_name,
                                input : diag_source_generator_common_inputs + [diag_attributes_yaml],
                                output : [test_name + '.generated.S',
                                          test_name + '.linker_script.ld'],
                                command : diag_source_generator_command)

  test_sources = [diag_source_generator_output[0]]
  linker_script = diag_source_generator_output[1].full_path()

  foreach suffix : source_suffixes
    if fs.is_file(meson.current_source_dir() + '/' + 'common' + '/' + test_name + suffix)
      test_sources += ['common' + '/' + test_name + suffix]
    elif get_option('rivos_internal_build') == true
      if fs.is_file(meson.current_source_dir() + '/' + 'rivos_internal' + '/' + test_name + suffix)
        test_sources += ['rivos_internal' + '/' + test_name + suffix]
      endif
    endif

  endforeach

  test_exe = executable(test_name,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  if get_option('diag_generate_disassembly') == true
    custom_target(test_name + '_dump',
                capture          : true,
                output           : test_name + '.dis',
                build_by_default : true,
                command          : [objdump, '-D', '-S', '-t', test_exe],
                depends          : [test_exe])
  endif

  if get_option('diag_target') == 'spike'
    spike_args = default_spike_args

    if spike_additional_arguments != ''
      spike_args += spike_additional_arguments.split()
    endif

    test(test_name + ' 🧪 ' + test_description,
          spike,
          args : [spike_args, test_exe],
          suite:'basic',
          should_fail: test_expected_to_fail)
  elif get_option('diag_target') == 'qemu'
    qemu_args = default_qemu_args

    if get_option('generate_trace') == true
      qemu_args += [
          '--var', 'ap-logfile:' + test_name + '.trace',
          '--var', 'out:' + meson.current_build_dir()
        ]
    endif

    test(test_name + ' 🧪 ' + test_description,
          qemu,
          args : [qemu_args, '--var', 'ap-payload:' + test_exe.full_path()],
          suite:'basic',
          timeout: get_option('qemu_timeout'),
          should_fail: test_expected_to_fail)
  endif

endforeach
