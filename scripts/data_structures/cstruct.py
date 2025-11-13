# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""C struct representation and manipulation utilities."""

field_type_to_size_in_bytes = {
    "uint8_t": 1,
    "uint16_t": 2,
    "uint32_t": 4,
    "uint64_t": 8,
}


class CStructField:
    """Represents a single field in a C struct."""

    def __init__(self, name, field_type, num_elements=1):
        self.name = name
        self.field_type = field_type
        self.num_elements = num_elements
        self.size_in_bytes = field_type_to_size_in_bytes[field_type]


class CStruct:
    """Represents a C struct with its fields and metadata."""

    def __init__(self, name, fields_data):
        self.name = name
        self.fields = []
        self.size_in_bytes = 0
        self.alignment = 8  # Hardcoded to 8-byte alignment
        self._parse_fields(fields_data)
        self._calculate_offsets_and_size()

    def _parse_fields(self, fields_data):
        """Parse field data from YAML into CStructField objects."""
        for field_name, field_spec in fields_data.items():
            if "," in field_spec:
                field_type, num_elements = field_spec.split(",")
                num_elements = int(num_elements.strip())
            else:
                field_type = field_spec
                num_elements = 1

            field = CStructField(field_name, field_type.strip(), num_elements)
            self.fields.append(field)

    def _calculate_offsets_and_size(self):
        """Calculate field offsets and total struct size."""
        current_offset = 0

        for field in self.fields:
            # Align field to its natural boundary
            while (current_offset % field.size_in_bytes) != 0:
                current_offset += 1

            field.offset = current_offset
            current_offset += field.size_in_bytes * field.num_elements

        # Align struct to specified boundary
        while (current_offset % self.alignment) != 0:
            current_offset += 1

        self.size_in_bytes = current_offset
