<!--
SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# JumpStart

Bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

## Setup the Environment

JumpStart requires the following tools to be available in your path:
* [meson](https://mesonbuild.com)
* [riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain)
* [Spike](https://github.com/riscv-software-src/riscv-isa-sim)
* [just](https://github.com/casey/just) (command runner)

### Ubuntu

Install required packages:
```shell
# gcc toolchain
# Install riscv-gnu-toolchain from source or use a prebuilt version

# just tool
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# meson
sudo apt install meson

# Build Spike from source
# See: https://github.com/riscv-software-src/riscv-isa-sim
```

### macOS

* Install the `gcc` toolchain to your path. Prebuilt binaries are available [HERE](https://docs.google.com/document/d/1-JRewN5ZJpFXSk_LkgvxqhzMnwZ_uRjPUb27tfEKRxc/edit#heading=h.jjddp8rb7042).
* Build a local copy of Spike and add it to your path. Instructions are available [HERE](https://docs.google.com/document/d/1egDH-BwAMEFCFvj3amu_VHRASCihpsHv70khnG6gojU/edit#heading=h.t75kh88x3knz).
* [brew](https://brew.sh) install `meson` and `just`.

JumpStart has been tested on Ubuntu 22.04 and macOS.

## Test the Environment

This will build JumpStart and run the unit tests.

```shell
just test gcc release spike
```

To see all the possible test targets, run:

```shell
just --list
```

## Building and Running Diags

The [`scripts/build_diag.py`](scripts/build_diag.py) script provides an easy way to build and run diags on different environments.

This will build the diag in the [`tests/common/test000`](tests/common/test000) using the `gcc` toolchain and run it on the `spike` environment:

```shell
❯ scripts/build_diag.py --diag_src_dir tests/common/test000/ --diag_build_dir /tmp/diag --environment spike
INFO: [ThreadPoolExecutor-0_0]: Compiling 'tests/common/test000/'
INFO: [ThreadPoolExecutor-1_0]: Running diag 'tests/common/test000/'
INFO: [MainThread]:
Summary
Build root: /tmp/diag
Build Repro Manifest: /tmp/diag/build_manifest.repro.yaml
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Diag                  ┃ Build        ┃ Run [spike]  ┃ Result                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ tests/common/test000/ │ PASS (2.20s) │ PASS (0.20s) │ /tmp/diag/test000/test000.elf │
└───────────────────────┴──────────────┴──────────────┴───────────────────────────────┘

Diagnostics built: 1
Diagnostics run: 1

Run Manifest:
/tmp/diag/run_manifest.yaml

STATUS: PASSED
```

For more details, check the Reference Manual section on [Building and Running Diags](docs/reference_manual.md#building-and-running-diags).

## Documentation

* [Quick Start: Anatomy of a Diag](docs/quick_start_anatomy_of_a_diag.md)
* [Reference Manual](docs/reference_manual.md)
* [FAQs](docs/faqs.md)
* [JumpStart Internals](docs/jumpstart_internals.md)

## Support

For help, please send a message on the Slack channel #jumpstart-directed-diags-framework.
