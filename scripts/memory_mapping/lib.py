# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import copy
import enum


class PageSize(enum.IntEnum):
    SIZE_4K = 0x1000
    SIZE_2M = 0x200000
    SIZE_1G = 0x40000000
    SIZE_512G = 0x8000000000


class MappingField:
    def __init__(
        self, name, field_type, input_yaml_type, allowed_values, default_value, required
    ) -> None:
        self.name = name
        self.field_type = field_type
        self.input_yaml_type = input_yaml_type
        self.allowed_values = allowed_values
        self.default_value = default_value
        self.required = required
        self.value = default_value

    def __str__(self) -> str:
        return f"MappingField(name={self.name}, value={self.value}, field_type={self.field_type}, input_yaml_type={self.input_yaml_type}, allowed_values={self.allowed_values}, default_value={self.default_value}, required={self.required})"

    def get_value(self):
        return self.value

    def check_value(self, value):
        if self.allowed_values is not None:
            assert (
                value in self.allowed_values
            ), f"Invalid value for field {self.name}: {value}. Allowed values are: {self.allowed_values}"

    def set_value_from_yaml(self, yaml_value):
        assert isinstance(yaml_value, self.input_yaml_type)

        if self.input_yaml_type == self.field_type:
            self.value = yaml_value
        elif self.input_yaml_type == str and self.field_type == int:
            if yaml_value.startswith("0x"):
                self.value = int(yaml_value, 16)
            elif yaml_value.startswith("0b"):
                self.value = int(yaml_value, 2)
            elif yaml_value.isnumeric():
                self.value = int(yaml_value)
            else:
                raise ValueError(f"Invalid value for field {self.name}: {yaml_value}")
        else:
            raise ValueError(f"Unable to convert {yaml_value} to {self.field_type}")

        self.check_value(self.value)

    def set_value(self, value):
        self.check_value(value)
        self.value = value


class MemoryMapping:
    def __init__(self, mapping_dict) -> None:
        self.fields = {
            "va": MappingField("va", int, int, None, None, False),
            "pa": MappingField("pa", int, int, None, None, True),
            "xwr": MappingField("xwr", int, str, [0, 1, 2, 3, 4, 5, 6, 7], None, False),
            "umode": MappingField("umode", int, str, [0, 1], None, False),
            "page_size": MappingField(
                "page_size",
                int,
                int,
                [PageSize.SIZE_4K, PageSize.SIZE_2M, PageSize.SIZE_1G, PageSize.SIZE_512G],
                None,
                True,
            ),
            "num_pages": MappingField("num_pages", int, int, None, None, True),
            "alias": MappingField("alias", bool, bool, None, False, False),
            "pma_memory_type": MappingField(
                "pma_memory_type", str, str, ["uc", "wc", "wb"], None, False
            ),
            "pbmt_mode": MappingField("pbmt_mode", str, str, ["io", "nc"], None, False),
            "linker_script_section": MappingField(
                "linker_script_section", str, str, None, None, False
            ),
            "valid": MappingField("umode", int, str, [0, 1], 1, False),
            "no_pte_allocation": MappingField("no_pte_allocation", bool, bool, None, False, False),
        }

        assert set(self.fields.keys()).issuperset(
            set(mapping_dict.keys())
        ), f"Mapping contains invalid fields: {mapping_dict.keys()}. Only {self.fields.keys()} are allowed."

        for field_name in self.fields.keys():
            if field_name not in mapping_dict.keys():
                if self.fields[field_name].required:
                    raise ValueError(
                        f"Field {field_name} is missing from the mapping: {mapping_dict}"
                    )
            else:
                self.fields[field_name].set_value_from_yaml(mapping_dict[field_name])

        self.sanity_check_field_values()

    def sanity_check_field_values(self):
        if self.get_field("pa") % self.get_field("page_size") != 0:
            raise ValueError(
                f"pa value {self.get_field('pa')} is not aligned with page_size {self.get_field('page_size')}"
            )

        if self.get_field("no_pte_allocation") is True:
            fields_not_allowed_for_no_pte_allocation = ["xwr", "umode", "va"]
            for field_name in fields_not_allowed_for_no_pte_allocation:
                assert (
                    self.get_field(field_name) is None
                ), f"{field_name} field is not allowed when no_pte_allocation is set to true"
        else:
            fields_required_for_pte_allocation = ["xwr", "va"]
            for field_name in fields_required_for_pte_allocation:
                assert (
                    self.get_field(field_name) is not None
                ), f"{field_name} field is required when no_pte_allocation is set to false"

        if self.get_field("alias") is True:
            if self.get_field("no_pte_allocation") is True:
                raise ValueError(
                    "alias and no_pte_allocation cannot be set to true at the same time"
                )
            fields_not_allowed_for_va_alias = [
                "linker_script_section",
                "pma_memory_type",
            ]
            for field_name in fields_not_allowed_for_va_alias:
                assert (
                    self.get_field(field_name) is None
                ), f"{field_name} field is not allowed when alias is set to true"

    def get_field(self, field_name):
        assert field_name in self.fields.keys()
        return self.fields[field_name].get_value()

    def set_field(self, field_name, value):
        assert field_name in self.fields.keys()
        self.fields[field_name].set_value(value)

    def __str__(self) -> str:
        return f"MemoryMapping({self.fields})"

    def copy(self):
        return copy.deepcopy(self)
