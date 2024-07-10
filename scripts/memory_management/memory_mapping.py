# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import copy

from .page_size import PageSize
from .page_tables import AddressType, TranslationStage


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
            "gpa": MappingField("gpa", int, int, None, None, False),
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
            "no_pte_allocation": MappingField("no_pte_allocation", bool, bool, None, None, False),
            "translation_stage": MappingField(
                "translation_stage", str, str, list(TranslationStage.stages.keys()), None, False
            ),
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

        self.set_translation_stage()

        self.sanity_check_field_values()

    def set_translation_stage(self):
        if self.get_field("translation_stage") is not None:
            return

        for stage in TranslationStage.get_enabled_stages():
            address_types = TranslationStage.stages[stage]["translates"]
            assert all([address_type in self.fields.keys() for address_type in address_types])
            if all([self.get_field(address_type) is not None for address_type in address_types]):
                assert (
                    self.get_field("no_pte_allocation") is not True
                ), "no_pte_allocation is explicitly set to True for a non-direct mapping"
                self.set_field("no_pte_allocation", False)

                self.set_field("translation_stage", stage)
                return

        # We're dealing with a direct mapping.
        assert (
            "pa" in self.fields.keys() and self.get_field("pa") is not None
        ), "PA is required for direct mapping"

        assert (
            self.get_field("no_pte_allocation") is not False
        ), "no_pte_allocation is explicitly set to False for a direct mapping"
        self.set_field("no_pte_allocation", True)

    def sanity_check_field_values(self):
        if self.get_field("pa") % self.get_field("page_size") != 0:
            raise ValueError(
                f"pa value {self.get_field('pa')} is not aligned with page_size {self.get_field('page_size')}"
            )

        if (
            self.get_field("translation_stage") is None
            and self.get_field("no_pte_allocation") is False
        ):
            raise ValueError("no_pte_allocation must be True for a direct mapping")
        if (
            self.get_field("translation_stage") is not None
            and self.get_field("no_pte_allocation") is True
        ):
            raise ValueError("no_pte_allocation must be False for a non-direct mapping")

        required_address_types = None
        if self.get_field("translation_stage") is not None:
            required_address_types = TranslationStage.get_address_types(
                self.get_field("translation_stage")
            )

            assert self.get_field("xwr") is not None, "xwr is required for non-direct mappings"
        else:
            required_address_types = {"pa"}

            assert all(
                [self.get_field(field_name) is None for field_name in ["xwr", "umode"]]
            ), "xwr and umode are not allowed for direct mappings"

            assert (
                self.get_field("alias") is False
            ), "alias must be set to False for direct mappings"

        assert all(
            [address_type in self.fields.keys() for address_type in required_address_types]
        ), f"Missing required address types: {required_address_types} when translation_stage is set to {self.get_field('translation_stage')}"

        disallowed_address_types = AddressType.get_all_address_types() - required_address_types
        assert all(
            [
                address_type in self.fields.keys() and self.get_field(address_type) is None
                for address_type in disallowed_address_types
            ]
        ), f"Disallowed address type in: {disallowed_address_types} when translation_stage is set to {self.get_field('translation_stage')}"

        if self.get_field("alias") is True:
            fields_not_allowed_for_va_alias = [
                "linker_script_section",
                "pma_memory_type",
            ]
            assert all(
                [
                    self.get_field(field_name) is None
                    for field_name in fields_not_allowed_for_va_alias
                ]
            ), f"{fields_not_allowed_for_va_alias} fields are not allowed when alias is set to True"

    def get_field(self, field_name):
        assert field_name in self.fields.keys()
        return self.fields[field_name].get_value()

    def set_field(self, field_name, value):
        assert field_name in self.fields.keys()
        self.fields[field_name].set_value(value)

    def __str__(self) -> str:
        print_string = "MemoryMapping("
        for field_name, field in self.fields.items():
            field_value = field.get_value()
            if isinstance(field_value, int):
                field_value = f"{hex(field_value)}"
            print_string += f"{field_name}={field_value}, "
        print_string += ")"

        return print_string

    def copy(self):
        return copy.deepcopy(self)
