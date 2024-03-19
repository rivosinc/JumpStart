<!--
SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# JumpStart

[![REUSE status](https://api.reuse.software/badge/github.com/rivosinc/JumpStart)](https://api.reuse.software/info/github.com/rivosinc/JumpStart)

Bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

## Getting Started

### Setup the Environment

JumpStart requires the following tools to be available in your path:
* [meson](https://mesonbuild.com)
* [riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)
* [Spike](https://github.com/riscv-software-src/riscv-isa-sim)

JumpStart has been tested on Ubuntu 22.04 and macOS.

### Test JumpStart

This will build JumpStart and run the unit tests.

```shell
meson setup builddir --cross-file cross_compile/public/gcc_options.txt --cross-file cross_compile/gcc.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

### Build an Example Diag

This will build a diag and run it on Spike.

```shell
meson setup builddir --cross-file cross_compile/public/gcc_options.txt --cross-file cross_compile/gcc.txt --buildtype release -Ddiag_attributes_yaml=tests/common/test000.diag_attributes.yaml -Ddiag_sources=tests/common/test000.c -Ddiag_name=my_jumpstart_diag
meson compile -C builddir
meson test -C builddir
```

## Documentation

* [Quick Start: Anatomy of a Diag](docs/quick_start_anatomy_of_a_diag.md)
* [Reference Manual](docs/reference_manual.md)
* [FAQs](docs/faqs.md)
* [JumpStart Internals](docs/jumpstart_internals.md)
