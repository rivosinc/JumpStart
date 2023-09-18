# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

subdir('common')

jumpstart_sources = jumpstart_common_sources

if get_option('rivos_internal_build') == true
  subdir('rivos_internal')
  jumpstart_sources += jumpstart_rivos_internal_sources
else
  subdir('public')
  jumpstart_sources += jumpstart_public_sources
endif
