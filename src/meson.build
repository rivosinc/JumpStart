# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

mmode_sources = []
smode_sources = []
umode_sources = []

subdir('common')

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
else
  subdir('public')
endif


jumpstart_sources = []

if 'mmode' in riscv_modes_in_build
  jumpstart_sources += mmode_sources
endif
if 'smode' in riscv_modes_in_build
  jumpstart_sources += smode_sources
endif
if 'umode' in riscv_modes_in_build
  jumpstart_sources += umode_sources
endif
