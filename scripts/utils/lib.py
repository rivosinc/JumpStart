#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generates the jumpstart source files from the jumpstart attributes YAML file.

import logging as log


class BitField:
    def extract_bits(value, bit_range):
        msb = bit_range[0]
        lsb = bit_range[1]
        return (value >> lsb) & ((1 << (msb - lsb + 1)) - 1)

    def place_bits(value, bits, bit_range):
        msb = bit_range[0]
        lsb = bit_range[1]
        return (value & ~(((1 << (msb - lsb + 1)) - 1) << lsb)) | (bits << lsb)


class ListUtils:
    def intersection(lst1, lst2):
        temp = set(lst2)
        lst3 = [value for value in lst1 if value in temp]
        return lst3


class DictUtils:
    def override_dict(original_dict, overrides_dict):
        assert set(original_dict.keys()).issuperset(
            set(overrides_dict.keys())
        ), "Overrides contain keys not present in the original dictionary"

        original_dict.update(overrides_dict)

    def create_dict(overrides_list):
        attributes_map = {}
        for override in overrides_list:
            key_value_pair = override.split("=")
            assert len(key_value_pair) == 2, "Invalid override: " + override

            attribute_name = override.split("=")[0]
            attribute_value = override.split("=")[1]

            if attribute_value.lower() == "true":
                attribute_value = True
            elif attribute_value.lower() == "false":
                attribute_value = False
            elif attribute_value.isnumeric():
                attribute_value = int(attribute_value)
            elif attribute_value.startswith("0x"):
                attribute_value = int(attribute_value, 16)
            elif attribute_value[0] == "[" and attribute_value[-1] == "]":
                attribute_value = attribute_value[1:-1].split(",")
                attribute_value = [x.strip() for x in attribute_value]

            attributes_map[attribute_name] = attribute_value
            log.debug(f"Command line overriding {attribute_name} with {attribute_value}.")

        return attributes_map
