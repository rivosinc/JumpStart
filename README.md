<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only
-->

# JumpStart

Provides bare-metal kernel and build infrastructure for users to build directed diags.

## Building a directed diag

To build a directed diag using user provided C file with `main()` and a memory map indicating the test memory layout:

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddirected_diag_memory_map_yaml=<PATH_TO_MEMORY_MAP_YAML> -Ddirected_diag_main_c=<PATH_TO_MAIN_C>
meson compile -C builddir
```

Example:
```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddirected_diag_memory_map_yaml=(pwd)/tests/test000.memory_map.yaml -Ddirected_diag_main_c=(pwd)/tests/test000.main.c
meson compile -C builddir
```

This will build `builddir/directed_diag`

## Testing JumpStart

Tests are in the [`tests/`](tests) directory.

JumpStart tests have a `main.c` and a memory map YAML file.

```
meson setup builddir --cross-file cross-file.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

## Page Table Generator

[`scripts/memory_map_tools.py`](scripts/memory_map_tools.py) takes a YAML file that has the program layout in memory and generates an assembly file with the page tables and a linker script that is used to build the directed diag ELF.

Example memory layout YAML: [`tests/test000.memory_map.yaml`](tests/test000.memory_map.yaml)

```
❯ ./scripts/memory_map_tools.py --help
usage: memory_map_tools.py [-h] --memory_map_file MEMORY_MAP_FILE [--output_assembly_file OUTPUT_ASSEMBLY_FILE]
                           [--output_linker_script OUTPUT_LINKER_SCRIPT] [--translate_VA TRANSLATE_VA] [-v]

options:
  -h, --help            show this help message and exit
  --memory_map_file MEMORY_MAP_FILE
                        Memory Map YAML file
  --output_assembly_file OUTPUT_ASSEMBLY_FILE
                        Assembly file to generate with page table mappings
  --output_linker_script OUTPUT_LINKER_SCRIPT
                        Linker script to generate
  --translate_VA TRANSLATE_VA
                        Translate the given VA to PA
  -v, --verbose         Verbose output.
```
