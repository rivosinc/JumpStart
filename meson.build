# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
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
                      # Let GCC know we are using our own malloc/calloc implementation. Otherwise
                      # it makes assumptions about using it's own.
                      '-fno-builtin',
                      '-mcmodel=medany',
                      language: 'c')

subdir('src')
subdir('include')

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

if get_option('diag_target') == 'spike'
  spike = find_program(get_option('spike_binary'))
  spike_isa_string = get_option('spike_isa_string')

  default_spike_args = []

  if get_option('rivos_internal_build') == true
    default_spike_args += rivos_spike_args
    if spike_isa_string == ''
      spike_isa_string = rivos_spike_isa_string
    endif

  else
    if spike_isa_string == ''
      spike_isa_string = 'rv64gch_zbb_zbs'
    endif

  endif

  if spike_isa_string != ''
    default_spike_args += ['--isa=' + spike_isa_string ]
  endif

  if get_option('generate_trace') == true
    default_spike_args += ['-l', '--log-commits']
  endif

  if get_option('spike_additional_arguments').length() > 0
    default_spike_args += get_option('spike_additional_arguments')
  endif

elif get_option('diag_target') == 'qemu'
  qemu_binary = rivos_qemu_binary
  if get_option('qemu_binary') != ''
    qemu_binary = get_option('qemu_binary')
  endif
  qemu = find_program(qemu_binary)

  default_qemu_args = rivos_qemu_args

  if get_option('qemu_additional_arguments').length() > 0
    default_qemu_args += get_option('qemu_additional_arguments')
  endif
endif

objdump = find_program('objdump')

gcc_march_string = get_option('gcc_march_string')

default_c_args_list = []

if gcc_march_string == ''
  if get_option('rivos_internal_build') == true
    gcc_march_string = rivos_gcc_march_string
  else
    gcc_march_string = 'rv64gc_zbb_zbs'
  endif
endif

default_c_args_list += ['-march=' + gcc_march_string]

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

  if get_option('diag_target') == 'qemu'
    diag_attribute_overrides += ['in_qemu_mode=True']
  endif

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

  if get_option('diag_generate_disassembly') == true
        custom_target('dump',
                capture          : true,
                output           : diag_name + '.dis',
                build_by_default : true,
                command          : [objdump, '-D', '-S', '-t', diag_exe],
                depends          : [diag_exe])
  endif

  if get_option('diag_target') == 'spike'
    test('🧪 ' + diag_name,
          spike,
          args : [default_spike_args, diag_exe],
          is_parallel : false) # Parallel runs of the test turns off terminal
                               # feedback and requires `reset` to be run to
                               # restore the terminal.
  elif get_option('diag_target') == 'qemu'
    qemu_args = default_qemu_args

    if get_option('generate_trace') == true
      qemu_args += [
          '--var', 'ap-logfile:' + diag_name + '.trace',
          '--var', 'out:' + meson.current_build_dir()
        ]
    endif

    test('🧪 ' + diag_name,
          qemu,
          timeout: get_option('qemu_timeout'),
          args : [qemu_args, '--var', 'ap-payload:' + diag_exe.full_path()])
  endif

else

  # Don't build the tests if we're building a diag.
  subdir('tests')

endif
