# SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import copy

from .page_size import PageSize
from .page_tables import AddressType, TranslationStage


class TranslationStageNoAddressTypesError(ValueError):
    """Raised when a translation stage cannot be assigned to a memory mapping."""

    pass


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
            if isinstance(value, list):
                assert all(
                    [v in self.allowed_values for v in value]
                ), f"Invalid value for field {self.name}: {value}. Allowed values are: {self.allowed_values}"
            else:
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
    supported_target_mmus = ["cpu"]

    def __init__(self, mapping_dict, max_num_cpus_supported=None) -> None:
        self.fields = {
            "va": MappingField("va", int, int, None, None, False),
            "gpa": MappingField("gpa", int, int, None, None, False),
            "pa": MappingField("pa", int, int, None, None, False),
            "spa": MappingField("spa", int, int, None, None, False),
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
            "num_pages": MappingField("num_pages", int, int, None, None, False),
            "num_pages_per_cpu": MappingField("num_pages_per_cpu", int, int, None, None, False),
            "alias": MappingField("alias", bool, bool, None, False, False),
            "pma_memory_type": MappingField(
                "pma_memory_type", str, str, ["uc", "wc", "wb", None], "uc", False
            ),
            "pbmt_mode": MappingField("pbmt_mode", str, str, ["pma", "io", "nc"], "pma", False),
            "linker_script_section": MappingField(
                "linker_script_section", str, str, None, None, False
            ),
            "valid": MappingField("umode", int, str, [0, 1], 1, False),
            "no_pte_allocation": MappingField("no_pte_allocation", bool, bool, None, None, False),
            "translation_stage": MappingField(
                "translation_stage", str, str, list(TranslationStage.stages.keys()), None, False
            ),
            "target_mmu": MappingField(
                "target_mmu", list, list, self.supported_target_mmus, ["cpu"], False
            ),
            "alignment": MappingField("alignment", int, int, None, None, False),
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

        if (
            mapping_dict.get("num_pages", None) is None
            and mapping_dict.get("num_pages_per_cpu", None) is None
        ):
            raise ValueError(
                f"num_pages or num_pages_per_cpu must be specified for the mapping: {mapping_dict}"
            )
        elif (
            mapping_dict.get("num_pages", None) is not None
            and mapping_dict.get("num_pages_per_cpu", None) is not None
        ):
            raise ValueError(
                f"num_pages and num_pages_per_cpu cannot both be specified for the mapping: {mapping_dict}"
            )

        # Convert num_pages_per_cpu to num_pages. We only need num_pages going forward.
        if mapping_dict.get("num_pages_per_cpu", None) is not None:
            if max_num_cpus_supported is None:
                raise ValueError(
                    "max_num_cpus_supported cannot be None when num_pages_per_cpu is not None"
                )
            self.fields["num_pages"].set_value(
                int(mapping_dict["num_pages_per_cpu"]) * max_num_cpus_supported
            )

        # Alias mappings should have no pma_memory_type.
        if self.get_field("alias") is True and mapping_dict.get("pma_memory_type") is None:
            self.set_field("pma_memory_type", None)

        self.set_translation_stage()

        self.sanity_check_field_values()

    @classmethod
    def get_supported_targets(self):
        return self.supported_target_mmus

    def set_translation_stage(self):
        if self.get_field("translation_stage") is not None:
            return

        address_types = [
            address_type
            for address_type in AddressType.get_all_address_types()
            if self.get_field(address_type) is not None
        ]

        if len(address_types) == 0:
            raise TranslationStageNoAddressTypesError(f"No address types set for mapping: {self}")

        if len(address_types) > 2:
            raise ValueError(f"Mapping has more than 2 address types set: {address_types}")

        for stage in TranslationStage.get_enabled_stages():
            if (
                len(address_types) == 2
                and TranslationStage.get_translates_from(stage) in address_types
                and TranslationStage.get_translates_to(stage) in address_types
            ):
                # we're dealing with a non-bare mapping for this stage.
                assert (
                    self.get_field("no_pte_allocation") is not True
                ), f"no_pte_allocation is explicitly set to True for a non-bare mapping: {self}"
                self.set_field("no_pte_allocation", False)

                self.set_field("translation_stage", stage)
                return
            elif (
                len(address_types) == 1
                and TranslationStage.get_translates_to(stage) in address_types
            ):
                # We're dealing with a direct mapping for this stage.
                assert (
                    self.get_field("no_pte_allocation") is not False
                ), f"no_pte_allocation is explicitly set to False for a direct mapping: {self}"
                self.set_field("no_pte_allocation", True)

                self.set_field("translation_stage", stage)
                return
            else:
                # Doesn't match this stage.
                continue

        raise ValueError(
            f"Unable to assign translation stage from among valid stages {TranslationStage.get_enabled_stages()} to mapping based on source and destination address types: {self}"
        )

    def is_bare_mapping(self):
        assert self.get_field("translation_stage") is not None
        return (
            self.get_field(TranslationStage.get_translates_to(self.get_field("translation_stage")))
            is not None
            and self.get_field(
                TranslationStage.get_translates_from(self.get_field("translation_stage"))
            )
            is None
        )

    def sanity_check_field_values(self):
        source_address_type = TranslationStage.get_translates_from(
            self.get_field("translation_stage")
        )
        destination_address_type = TranslationStage.get_translates_to(
            self.get_field("translation_stage")
        )

        # Check that we have a destination address for this mapping
        assert (
            self.get_field(TranslationStage.get_translates_to(self.get_field("translation_stage")))
            is not None
        ), f"Missing destination address for mapping: {self}"

        if self.get_field(destination_address_type) % self.get_field("page_size") != 0:
            raise ValueError(
                f"{destination_address_type.upper()} value {self.get_field(destination_address_type)} is not aligned with page_size {self.get_field('page_size')}"
            )

        # Check that we only have the allowed set of address types set for this
        # mapping.
        disallowed_address_types = AddressType.get_all_address_types()
        disallowed_address_types.remove(destination_address_type)
        if (
            TranslationStage.get_selected_mode_for_stage(self.get_field("translation_stage"))
            != "bare"
        ):
            # Only non-bare mappings can have source address type set.
            disallowed_address_types.remove(source_address_type)

        for address_type in disallowed_address_types:
            assert address_type in self.fields.keys()
            if self.get_field(address_type) is not None:
                raise ValueError(
                    f"Address type '{address_type}' invalid for translation stage '{self.get_field('translation_stage')}' with translation mode '{TranslationStage.get_selected_mode_for_stage(self.get_field('translation_stage'))}' in mapping:\n{self}\n\n"
                )

        # Make sure that there are only 2 address types set for this mapping.
        address_types = [
            address_type
            for address_type in AddressType.get_all_address_types()
            if self.get_field(address_type) is not None
        ]

        assert (
            len(address_types) <= 2
        ), f"Mapping has more than 2 address types set: {address_types}"

        if self.is_bare_mapping():
            assert all(
                [self.get_field(field_name) is None for field_name in ["xwr", "umode"]]
            ), "xwr and umode are not allowed for direct mappings"

            assert (
                self.get_field("alias") is False
            ), "alias must be set to False for direct mappings"
        else:
            assert self.get_field("xwr") is not None, "xwr is required for non-bare mappings"

        if self.get_field("alias") is True:
            fields_not_allowed_for_alias_mappings = [
                "linker_script_section",
                "pma_memory_type",
            ]
            assert all(
                [
                    self.get_field(field_name) is None
                    for field_name in fields_not_allowed_for_alias_mappings
                ]
            ), f"{fields_not_allowed_for_alias_mappings} fields are not allowed when alias is set to True"

        if (
            self.get_field("no_pte_allocation") is False
            and self.get_field("translation_stage") == "g"
            and self.get_field("umode") != 1
        ):
            raise ValueError(f"umode not set to 1 for g stage mapping: {self}")

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
