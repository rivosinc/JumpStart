# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

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

subdir('src')

jumpstart_includes = include_directories('include')

prog_python = find_program('python3')
jumpstart_source_generator = files('scripts/generate_jumpstart_sources.py')

jumpstart_source_generator_inputs = [jumpstart_source_generator, jumpstart_source_attributes_yaml]
jumpstart_source_generator_expected_outputs = ['jumpstart_defines.h', 'jumpstart_data_structures.h', 'jumpstart_data_structures.S']
jumpstart_source_generator_command = [prog_python,
                                              '@INPUT0@',
                                              '--defines_file', '@OUTPUT0@',
                                              '--data_structures_file', '@OUTPUT1@',
                                              '--assembly_file', '@OUTPUT2@',
                                              '--jumpstart_source_attributes_yaml', '@INPUT1@',
                                              ]

jumpstart_source_generator_outputs = custom_target(
                                      'Generate jumpstart sources for build',
                                      input : jumpstart_source_generator_inputs,
                                      output: jumpstart_source_generator_expected_outputs,
                                      command: jumpstart_source_generator_command)

jumpstart_sources += jumpstart_source_generator_outputs

diag_source_generator = files('scripts/generate_diag_sources.py')

diag_sources = get_option('diag_sources')
diag_attributes_yaml = get_option('diag_attributes_yaml')


spike = find_program(get_option('spike_binary'))

spike_isa_string = get_option('spike_isa_string')
gcc_march_string = get_option('gcc_march_string')

default_spike_args = []

if get_option('rivos_internal_build') == true
  default_spike_args += rivos_spike_args

  if spike_isa_string == ''
    spike_isa_string = rivos_spike_isa_string
  endif

  if gcc_march_string == ''
    gcc_march_string = rivos_gcc_march_string
  endif
endif

if gcc_march_string == ''
  gcc_march_string = 'rv64gc_zicbom'
endif

if spike_isa_string != ''
  default_spike_args += ['--isa=' + spike_isa_string ]
endif

if get_option('spike_generate_trace') == true
  default_spike_args += ['-l', '--log-commits']
endif

if get_option('spike_additional_arguments').length() > 0
  default_spike_args += get_option('spike_additional_arguments')
endif

default_c_args_list = ['-march=' + gcc_march_string]

diag_source_generator_common_inputs = [diag_source_generator, jumpstart_source_attributes_yaml]
diag_source_generator_command = [prog_python,
                                    '@INPUT0@',
                                    '--jumpstart_source_attributes_yaml', '@INPUT1@',
                                    '--diag_attributes_yaml', '@INPUT2@',
                                    '--output_assembly_file', '@OUTPUT0@',
                                    '--output_linker_script', '@OUTPUT1@',
                                    ]

if diag_attributes_yaml != '' and diag_sources.length() > 0
  diag_name = get_option('diag_name')

  diag_attribute_overrides = get_option('diag_attribute_overrides')
  if diag_attribute_overrides.length() > 0
    diag_source_generator_command += ['--override_diag_attributes']

    foreach override : diag_attribute_overrides
      diag_source_generator_command += [override]
    endforeach
  endif

  diag_source_generator_output = custom_target(
                                'Generate diag attributes related source files for ' + diag_name,
                                input : diag_source_generator_common_inputs + [diag_attributes_yaml],
                                output : ['generated_diag_source.S',
                                          'linker_script.ld'],
                                command : diag_source_generator_command)

  diag_sources += diag_source_generator_output[0]
  linker_script = diag_source_generator_output[1].full_path()

  diag_exe = executable(diag_name,
                        sources: [jumpstart_sources, diag_sources],
                        include_directories: jumpstart_includes,
                        c_args: default_c_args_list,
                        link_args: ['-T' + linker_script, '-nostdlib'])

  test('🧪 ' + diag_name,
        spike,
        args : [default_spike_args, diag_exe])

else

  # Don't build the tests if we're building a diag.
  subdir('tests')

endif
