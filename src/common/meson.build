# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

mmode_sources += files('jumpstart.mmode.S',
                       'trap_handler.mmode.c',
                       'utils.mmode.c',
                       'data.privileged.S')

smode_sources += files('jumpstart.smode.S',
                              'jumpstart.vsmode.S',
                              'tablewalk.smode.c',
                              'trap_handler.smode.c',
                              'string.smode.c',
                              'time.smode.c',
                              'utils.smode.c',
                              'uart.smode.c',
                              'heap.smode.c',
                              'heap.smode.S',
                              'lock.smode.c')

if get_option('boot_config') == 'fw-sbi'
  smode_sources += files(
                          'sbi_firmware_boot.smode.S',
                        )
endif

umode_sources += files('jumpstart.umode.S',
                       'jumpstart.vumode.S')
