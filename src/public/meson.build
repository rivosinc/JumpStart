# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

jumpstart_public_sources = files(
                          'jump_to_main.mmode.S',
                          'end.mmode.S'
                          )
jumpstart_public_drivers = []

subdir('uart')

jumpstart_public_sources += jumpstart_public_drivers

jumpstart_source_attributes_yaml = files('jumpstart_public_source_attributes.yaml')
