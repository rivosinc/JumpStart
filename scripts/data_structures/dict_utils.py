# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log


class DictUtils:
    def override_dict(
        original_dict, overrides_dict, original_is_superset=True, append_to_lists=False
    ):
        if original_is_superset is True:
            assert set(original_dict.keys()).issuperset(
                set(overrides_dict.keys())
            ), "Overrides contain keys not present in the original dictionary"

        if append_to_lists is False:
            original_dict.update(overrides_dict)
        else:
            for key in overrides_dict:
                if key in original_dict and isinstance(original_dict[key], list):
                    if isinstance(overrides_dict[key], list):
                        original_dict[key].extend(overrides_dict[key])
                    else:
                        original_dict[key].append(overrides_dict[key])
                else:
                    original_dict[key] = overrides_dict[key]

    def create_dict(overrides_list):
        attributes_map = {}
        for override in overrides_list:
            # Split at the first '='
            name_value_pair = override.split("=", 1)

            attribute_name = name_value_pair[0]
            attribute_value = name_value_pair[1]

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
