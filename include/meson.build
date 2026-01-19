# SPDX-FileCopyrightText: 2023 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

jumpstart_include_dirs_list = ['common']

if get_option('rivos_internal_build') == true
  jumpstart_include_dirs_list += ['rivos_internal']
endif

jumpstart_includes = include_directories(jumpstart_include_dirs_list)
