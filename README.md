<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only
-->

# JumpStart

Provides bare-metal kernel and build infrastructure for writing and building directed diags.

## Setup Environment

```
module load rivos/init
module load rivos-sdk/riscv-isa-sim
module load rivos-sdk/riscv-gnu-toolchain
```

**Note**: If the latest toolchain is not available for your distro, pick the specific toolchain package available for your installed distro.

### Test Environment

```
meson setup builddir --cross-file cross-file.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```

## Writing and Building Diags

The Jumpstart [`tests/`](tests) are a good reference on writing diags. This [file](tests/meson.build) has the list of tests and a description of each of them.

Jumpstart provides a set of basic API functions that help with writing diags. These are listed in [jumpstart_functions.h](jumpstart_functions.h).

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

**The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for jumpstart purposes and should not be used in diags.** TP is used to point to a per hart attributes structure and GP is used as a temporary in jumpstart routines.

Diags are expected to provide sources (C and assembly files) and it's attributes in a YAML file.

For example, `test003` has:
* Sources
  * [test003.c](tests/test003.c)
  * [test003.S](tests/test003.S)
* Test Attribute File:
  * [test003.memory_map.yaml](tests/test003.memory_map.yaml)

### Test Attributes File

The Test Attributes File specifies the memory layout and various attributes of the test such as the MMU mode, number of active harts, etc.

These test attributes can be overriden from the command line at setup time using the meson option `diag_attribute_overrides`.

#### Memory Layout

The following memory map layout:

```
mappings:
  -
    va: 0x80000000
    pa: 0x80000000
    xwr: "0b101"
    page_size: 0x1000
    num_pages: 1
    pmarr_memory_type: "wb"
    linker_script_section: ".text"
  -
    va: 0x80002000
    pa: 0x80002000
    xwr: "0b011"
    page_size: 0x1000
    num_pages: 1
    pmarr_memory_type: "wb"
    linker_script_section: ".data"
  -
    va: 0x80003000
    pa: 0x80003000
    xwr: "0b101"
    umode: "0b1"
    page_size: 0x1000
    num_pages: 2
    pmarr_memory_type: "wb"
    linker_script_section: ".text.umode"
  -
    va: 0x80005000
    pa: 0x80005000
    xwr: "0b011"
    umode: "0b1"
    page_size: 0x1000
    num_pages: 1
    pmarr_memory_type: "wb"
    linker_script_section: ".data.umode"
```

specifies the 4 sections of a diag as well as their VA, page protection attributes (xwr, umode), memory type (pmarr_memory_type) as well as the linker section that they will be placed in.

### Running diags in M/S/U modes

Jumpstart will initialize the system and jump to the diag `main()`.

By default, `main()` will be called in S-mode. To enter `main()` in M-mode, set the `start_test_in_machine_mode` attribute to `True` in the Attribute file (See [test009's Attribute File](tests/test009.memory_map.yaml) for an example).

Diags can use the `run_function_in_user_mode()` API to run specific functions in user mode. The sections containing U-mode code have to be tagged with the `umode` attribute in the Memory Map in the Attributes file.
Refer to `test002` and `test011` as examples for writing U-mode tests.

### MP diags

The active harts in a diag are indicated by setting the `active_hart_mask` test attribute.

```
active_hart_mask: "0b1111"
```

**NOTE: Spike takes the number of active cores and not a bitmask so a diag built with non-consecutive harts enabled in the `active_hart_mask` mask cannot be run on Spike.**

**NOTE: The UART APIs have not been tested with MP diags.**


### Building Diags

Pass the sources and the attribute file to `meson setup` with the `-Ddiag_memory_map_yaml`, `-Ddiag_name` and `-Ddiag_sources` build flags:


```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_memory_map_yaml=<PATH_TO_MEMORY_MAP_YAML> -Ddiag_sources=<COMMA SEPARATED LIST OF SOURCE FILES> -Ddiag_name=<DIAG NAME>
meson compile -C builddir
```

Example:
```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_memory_map_yaml=(pwd)/tests/test000.memory_map.yaml -Ddiag_sources=(pwd)/tests/test000.c -Ddiag_name=my_jumpstart_diag
meson compile -C builddir
```

This will build `builddir/my_jumpstart_diag`

## Support

For help, please send a message on the Slack channel #jumpstart-directed-diags-framework.
