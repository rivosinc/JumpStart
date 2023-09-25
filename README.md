<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# JumpStart

Bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

## Getting Started

### Setup the Environment

#### Ubuntu or CentOS VMs

```
module load rivos/init
module load rivos-sdk/riscv-isa-sim
module load rivos-sdk/riscv-gnu-toolchain
```

#### macOS

* Install the riscv-gnu-toolchain to your path. Prebuilt binaries are available [HERE](https://docs.google.com/document/d/1-JRewN5ZJpFXSk_LkgvxqhzMnwZ_uRjPUb27tfEKRxc/edit#heading=h.jjddp8rb7042).
* Build a local copy of Spike and add it to your path. Instructions are available [HERE](https://docs.google.com/document/d/1egDH-BwAMEFCFvj3amu_VHRASCihpsHv70khnG6gojU/edit#heading=h.t75kh88x3knz).
* [brew](https://brew.sh) install `meson`.


### Test JumpStart

This will build JumpStart and run the unit tests.

```
meson setup builddir --cross-file cross-file.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

## Documentation

* [Quick Start: Anatomy of a Diag](docs/quick_start_anatomy_of_a_diag.md)
* [Reference Manual](docs/reference_manual.md)
* [FAQs](docs/faqs.md)
* [Jumpstart Internals](docs/jumpstart_internals.md)

## Support

For help, please send a message on the Slack channel #jumpstart-directed-diags-framework.
