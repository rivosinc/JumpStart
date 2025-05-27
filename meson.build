# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

project('JumpStart', 'c',
        default_options : [
          'warning_level=3',
          'werror=true',
          'b_ndebug=if-release',
          ],
        meson_version: '>=1.3.0'
)

# Check compiler support for mcmodel options
cc = meson.get_compiler('c')
mcmodel = get_option('mcmodel')
if not cc.has_argument('-mcmodel=' + mcmodel)
  error('Selected mcmodel=' + mcmodel + ' but compiler does not support it. Please use a different mcmodel option.')
endif

add_project_arguments('-Wno-pedantic',
                      # Require that all enums are covered by a switch statement.
                      '-Wswitch-enum',
                      # Check for implicit fallthrough in switch statements.
                      '-Wimplicit-fallthrough',
                      '-Wunreachable-code',
                      # Let GCC know we are using our own malloc/calloc implementation. Otherwise
                      # it makes assumptions about using it's own.
                      '-fno-builtin',
                      '-mcmodel=' + mcmodel,
                      language: 'c')

diag_custom_defines = get_option('diag_custom_defines')
foreach diag_custom_define : diag_custom_defines
  add_project_arguments('-D' + diag_custom_define, language : 'c')
endforeach

default_c_args = []

diag_attribute_overrides = get_option('diag_attribute_overrides')

compatible_priv_modes = []
if get_option('boot_config') == 'fw-none'
  compatible_priv_modes = get_option('riscv_priv_modes_enabled')
else
  error('Invalid boot_config value. Only fw-none is supported.')
endif

riscv_priv_modes_enabled = []
foreach mode: get_option('riscv_priv_modes_enabled')
    if compatible_priv_modes.contains(mode)
      riscv_priv_modes_enabled += [mode]
    endif
endforeach


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
                                              '--priv_modes_enabled', riscv_priv_modes_enabled
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
      spike_isa_string = 'rv64gcvh_zba_zbb_zbs_zkr_svpbmt_smstateen_zicntr'
    endif

    default_spike_args += ['--misaligned']

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

diag_source_generator_common_inputs = [diag_source_generator, jumpstart_source_attributes_yaml]
diag_source_generator_command = [prog_python,
                                    '@INPUT0@',
                                    '--jumpstart_source_attributes_yaml', '@INPUT1@',
                                    '--diag_attributes_yaml', '@INPUT2@',
                                    '--output_assembly_file', '@OUTPUT0@',
                                    '--output_defines_file', '@OUTPUT2@',
                                    '--output_linker_script', '@OUTPUT1@',
                                    '--priv_modes_enabled', riscv_priv_modes_enabled
                                    ]

if get_option('diag_target') == 'qemu'
  diag_attribute_overrides += ['in_qemu_mode=True']
endif

if diag_attribute_overrides.length() > 0
  diag_source_generator_command += ['--override_diag_attributes']

  foreach override : diag_attribute_overrides
    diag_source_generator_command += [override]
  endforeach
endif

if diag_attributes_yaml != '' and diag_sources.length() > 0
  diag_name = get_option('diag_name')

  diag_source_generator_output = custom_target(
                                'Generate diag attributes related source files for ' + diag_name,
                                input : diag_source_generator_common_inputs + [diag_attributes_yaml],
                                output : [diag_name + '.generated.S',
                                          diag_name + '.linker_script.ld',
                                          diag_name + '.defines.h'],
                                command : diag_source_generator_command)

  diag_sources += diag_source_generator_output[0]
  linker_script = diag_source_generator_output[1]
  diag_defines = diag_source_generator_output[2]

  diag_exe = executable(diag_name + '.elf',
                        sources: [jumpstart_sources, diag_sources],
                        include_directories: jumpstart_includes,
                        c_args: ['-include', diag_defines.full_path()],
                        link_args: ['-T' + linker_script.full_path()],
                        link_depends: linker_script,
                        dependencies: declare_dependency(sources: diag_defines)
                        )

  if get_option('diag_generate_disassembly') == true
        custom_target('dump',
                capture          : true,
                output           : diag_name + '.dis',
                build_by_default : true,
                command          : [objdump, '-D', '-S', '-t', diag_exe],
                depends          : [diag_exe])
  endif

  trace_file = diag_name + '.itrace'

  if get_option('diag_target') == 'spike'
    spike_args = default_spike_args

    if get_option('generate_trace') == true
      spike_args += ['--log=' + trace_file]
    endif

    target = spike
    args = [spike_args, diag_exe]
    timeout = get_option('spike_timeout')

    test('🧪 ' + diag_name,
          target,
          args : args,
          timeout: timeout,
          depends: diag_exe,
          should_fail: false
        )
  endif

else

  # Don't build the tests if we're building a diag.
  subdir('tests')

endif
