<!--
SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# JumpStart

[![REUSE status](https://api.reuse.software/badge/github.com/rivosinc/JumpStart)](https://api.reuse.software/info/github.com/rivosinc/JumpStart)

Bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

## Setup the Environment

JumpStart requires the following tools to be available in your path:
* [meson](https://mesonbuild.com)
* [riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)
* [Spike](https://github.com/riscv-software-src/riscv-isa-sim)

JumpStart has been tested on Ubuntu 22.04 and macOS.

## Test the Environment

This will build JumpStart and run the unit tests.

```shell
meson setup builddir --cross-file cross_compile/public/gcc_options.txt --cross-file cross_compile/gcc.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

## Building and Running Diags

The [`scripts/build_diag.py`](scripts/build_diag.py) script provides an easy way to build and run diags on different targets.

This will build the diag in the [`tests/common/test000`](tests/common/test000) using the `gcc` toolchain and run it on the `spike` target:

```shell
❯ scripts/build_diag.py --diag_src_dir tests/common/test000/ --diag_build_dir /tmp/diag
INFO: [MainThread]: Diag built:
        Name: test000
        Directory: /tmp/diag
        Assets: {'disasm': '/tmp/diag/test000.elf.dis', 'binary': '/tmp/diag/test000.elf', 'spike_trace': '/tmp/diag/test000.itrace'}
        BuildType: release,
        Target: spike
        RNG Seed: 8410517908284574883
        Source Info:
                Diag: test000, Source Path: /Users/joy/workspace/jumpstart/tests/common/test000
                Sources: ['/Users/joy/workspace/jumpstart/tests/common/test000/test000.c']
                Attributes: /Users/joy/workspace/jumpstart/tests/common/test000/test000.diag_attributes.yaml
                Meson options overrides file: None
```

## Documentation

* [Quick Start: Anatomy of a Diag](docs/quick_start_anatomy_of_a_diag.md)
* [Reference Manual](docs/reference_manual.md)
* [FAQs](docs/faqs.md)
* [JumpStart Internals](docs/jumpstart_internals.md)
