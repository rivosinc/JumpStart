# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

project('JumpStart', 'c')

linker_script = meson.current_source_dir() + '/link.ld'

jumpstart_test = executable('jumpstart',
                            files('main.c', 'helper_functions.c', 'start.s'),
                            c_args: ['-nostdlib'],
                            link_args: ['-T' + linker_script, '-nostdlib'])

install_headers('helper_functions.h')

spike = find_program('spike', required : true)

test('run jumpstart on Spike',
      spike, args : [jumpstart_test])
