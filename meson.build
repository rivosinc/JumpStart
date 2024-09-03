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

add_project_arguments('-Wno-pedantic',
                      # Require that all enums are covered by a switch statement.
                      '-Wswitch-enum',
                      # Check for implicit fallthrough in switch statements.
                      '-Wimplicit-fallthrough',
                      '-Wunreachable-code',
                      # Let GCC know we are using our own malloc/calloc implementation. Otherwise
                      # it makes assumptions about using it's own.
                      '-fno-builtin',
                      '-mcmodel=medany',
                      language: 'c')



jumpstart_source_attribute_overrides = get_option('jumpstart_source_attribute_overrides')
diag_attribute_overrides = get_option('diag_attribute_overrides')

if get_option('batch_mode') == true
  if get_option('boot_config') != 'fw-m'
    error('batch_mode=true requires boot_config=fw-m')
  endif
  if get_option('diag_target') == 'spike'
    error('batch_mode=true only supported on diag_target=qemu')
  endif
  diag_attribute_overrides += ['batch_mode=true']
endif

compatible_priv_modes = []
if get_option('boot_config') == 'fw-none'
  compatible_priv_modes = get_option('riscv_priv_modes_enabled')
elif get_option('boot_config') == 'fw-m'
  compatible_priv_modes = ['mmode', 'smode', 'umode']
  jumpstart_source_attribute_overrides += ['diag_entry_label=_mmode_start']
  if get_option('batch_mode') == false
    # fw-m expects the bare-metal workload to start at a fixed address.
    diag_attribute_overrides += ['mmode_start_address=' + '0x90000000']
  else
    # The batch mode runtime is expected to start at the fixed address
    # so we need to start the diag at a higher offset.
    diag_attribute_overrides += ['mmode_start_address=' + '0x98000000']
  endif
elif get_option('boot_config') == 'fw-sbi'
  compatible_priv_modes = ['smode', 'umode']
  jumpstart_source_attribute_overrides += ['diag_entry_label=sbi_firmware_trampoline']
  diag_attribute_overrides += ['smode_start_address=' + '0x90000000']
else
  error('Invalid boot_config value')
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

override_jumpstart_source_attributes_parameter = []
if jumpstart_source_attribute_overrides.length() > 0
  override_jumpstart_source_attributes_parameter += ['--override_jumpstart_source_attributes']

  foreach override : jumpstart_source_attribute_overrides
    override_jumpstart_source_attributes_parameter += [override]
  endforeach
endif
jumpstart_source_generator_command += override_jumpstart_source_attributes_parameter

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
      spike_isa_string = 'rv64gcvh_zbb_zbs_zkr_svpbmt_smstateen'
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

diag_source_generator_command += override_jumpstart_source_attributes_parameter

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

  diag_exe = executable(diag_name,
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

  if get_option('diag_target') == 'spike'
    test('🧪 ' + diag_name,
          spike,
          args : [default_spike_args, diag_exe],
          timeout: get_option('spike_timeout'),
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
