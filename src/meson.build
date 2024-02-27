# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

mmode_sources = []
smode_sources = []
umode_sources = []

jumpstart_sources = []

subdir('common')

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
else
  subdir('public')
endif

jumpstart_sources = mmode_sources + smode_sources + umode_sources
