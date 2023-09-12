# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

jumpstart_sources = files(
                          'start.machine.S',
                          'jumpstart_functions.supervisor.S',
                          'jumpstart_functions.umode.S',
                          'data.privileged.S',
                          'end.machine.S',
                          'imsic_functions.supervisor.c',
                          'string_functions.supervisor.c',
                          'tablewalk_functions.supervisor.c',
                          'trap_handler_functions.supervisor.c',
                          'uart_functions.supervisor.c',
                          )

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
  jumpstart_sources += jumpstart_rivos_internal_sources

  jumpstart_source_attributes_yaml = jumpstart_internal_source_attributes_yaml
else

  jumpstart_source_attributes_yaml = files('jumpstart_public_source_attributes.yaml')
endif
