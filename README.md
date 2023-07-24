<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only
-->

# JumpStart

Provides bare-metal kernel and build infrastructure for test writers to build directed diags.

## Setup Environment

```
module load rivos/init
module load rivos-sdk/riscv-isa-sim
module load rivos-sdk/riscv-gnu-toolchain
```

**Note**: If the latest toolchain is not available for your distro, pick the specific toolchain package available for your installed distro.

### Testing Environment

```
meson setup builddir --cross-file cross-file.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

## Build a directed diag

Diags are expected to provide sources (C and assembly files) and a map of it's memory layout.

Jumpstart will initialize the system and jump to the diag `main()`.

The Jumpstart API functions are listed in [jumpstart_functions.h](jumpstart_functions.h).

The Jumpstart [`tests/`](tests) are a good reference on writing diags. This [file](tests/meson.build) has the list of tests and a description of each of them.

To build a directed diag using user provided source files (C and assembly) and a memory map indicating the diag memory layout:

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_memory_map_yaml=<PATH_TO_MEMORY_MAP_YAML> -Ddiag_sources=<COMMA SEPARATED LIST OF SOURCE FILES>
meson compile -C builddir
```

Example:
```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_memory_map_yaml=(pwd)/tests/test000.memory_map.yaml -Ddiag_sources=(pwd)/tests/test000.c
meson compile -C builddir
```

This will build `builddir/diag`
