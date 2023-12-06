# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

subdir('common')

jumpstart_tests = common_jumpstart_tests

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
  jumpstart_tests += rivos_internal_jumpstart_tests
endif

if get_option('diag_target') == 'qemu'
  diag_source_generator_command += ['--override_diag_attributes=in_qemu_mode=True']
endif


foreach jumpstart_test : jumpstart_tests
  test_prefix = jumpstart_test.get(0)
  test_description = jumpstart_test.get(1)
  test_expected_to_fail = jumpstart_test.get(2, false)

  spike_additional_arguments = jumpstart_test.get(3, '')

  test_disabled_on_qemu = jumpstart_test.get(4, false)

  if fs.is_file(meson.current_source_dir() + '/' + 'common' + '/' + test_prefix + '.diag_attributes.yaml')
    diag_attributes_yaml = files('common' + '/' + test_prefix + '.diag_attributes.yaml')
  elif get_option('rivos_internal_build') == true
    if fs.is_file(meson.current_source_dir() + '/' + 'rivos_internal' + '/' + test_prefix + '.diag_attributes.yaml')
      diag_attributes_yaml = files('rivos_internal' + '/' + test_prefix + '.diag_attributes.yaml')
    endif
  endif

  diag_source_generator_output = custom_target(
                                'Generate diag attributes related source files for ' + test_prefix,
                                input : diag_source_generator_common_inputs + [diag_attributes_yaml],
                                output : [test_prefix + '.generated.S',
                                          test_prefix + '.linker_script.ld'],
                                command : diag_source_generator_command)

  test_sources = [diag_source_generator_output[0]]
  linker_script = diag_source_generator_output[1].full_path()

  foreach suffix : source_suffixes
    if fs.is_file(meson.current_source_dir() + '/' + 'common' + '/' + test_prefix + suffix)
      test_sources += ['common' + '/' + test_prefix + suffix]
    elif get_option('rivos_internal_build') == true
      if fs.is_file(meson.current_source_dir() + '/' + 'rivos_internal' + '/' + test_prefix + suffix)
        test_sources += ['rivos_internal' + '/' + test_prefix + suffix]
      endif
    endif

  endforeach

  test_exe = executable(test_prefix,
                        sources: [jumpstart_sources, test_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  if get_option('diag_generate_disassembly') == true
    custom_target(test_prefix + '_dump',
                capture          : true,
                output           : test_prefix + '.dis',
                build_by_default : true,
                command          : [objdump, '-D', '-S', '-t', test_exe],
                depends          : [test_exe])
  endif

  if get_option('diag_target') == 'spike'
    spike_args = default_spike_args

    if spike_additional_arguments != ''
      spike_args += spike_additional_arguments.split()
    endif

    test(test_prefix + ' 🧪 ' + test_description,
          spike,
          args : [spike_args, test_exe],
          suite:'basic',
          should_fail: test_expected_to_fail)
  elif get_option('diag_target') == 'qemu' and test_disabled_on_qemu == false
    test(test_prefix + ' 🧪 ' + test_description,
          qemu,
          args : [default_qemu_args, '--var', 'ap-payload:' + test_exe.full_path()],
          suite:'basic',
          should_fail: test_expected_to_fail)
  endif

endforeach
