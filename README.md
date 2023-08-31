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

The Jumpstart [`Unit Tests`](tests) are a good reference on writing diags. This [file](tests/meson.build) has the list of unit tests and a description of each of them.

Jumpstart provides a set of basic API functions that help with writing diags. These are listed in [jumpstart_functions.h](jumpstart_functions.h).

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

**The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for jumpstart purposes and should not be used in diags.** TP is used to point to a per hart attributes structure and GP is used as a temporary in jumpstart routines.

Diags are expected to provide sources (C and assembly files) and it's attributes in a YAML file.

For example, `test003` has:
* Sources
  * [test003.c](tests/test003.c)
  * [test003.S](tests/test003.S)
* Test Attribute File:
  * [test003.test_attributes.yaml](tests/test003.test_attributes.yaml)

### Diag Attributes File

The Diag Attributes File specifies the memory layout and various attributes of the diag such as the MMU mode, number of active harts, etc.

#### Memory Layout Examples

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

```
mappings:
  -
    pa: 0x80000000
    page_size: 0x1000
    num_pages: 2
    pmarr_memory_type: "wb"
    no_pte_allocation: True
    linker_script_section: ".text"
```

The specified section will be placed in the executable but no mapping will be created for it in the page table map. It doesn't have the attributes that an entry with a page table entry would have such as xwr, va, umode.

#### Updating Page Tables

The page tables are generated from the memory map. Page tables are only generated for mappings with the `no_pte_allocation` attribute set to `false`. The maximum number of pages that can be used to allocate Page Tables is controlled by `max_num_pages_for_PT_allocation`.

The Page Tables are marked Read Only by default. This prevents accidental modification of the page tables from supervisor mode.

To enable page table modification, set the `allow_page_table_modifications` to `true` diag attribute. This will enable the write permissions in the page table entries for the Page Table area.

#### Overriding Diag Attributes

Certain diag attributes can be overriden from the command line at setup time using the meson option `diag_attribute_overrides` which takes a list of attributes that can be overriden.

Examples:

* Overriding the `active_hart_mask` (the default is `0b1` or 1 hart active):

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attribute_overrides=active_hart_mask=0b11 -Ddiag_attributes_yaml=<ATTRIBUTES> -Ddiag_sources=<SOURCES> -Ddiag_name=<NAME>
```

* QEMU expects 4 harts to be active and a separate diag termination procedure which is enabled by setting `in_qemu_mode` to `True`:

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attribute_overrides=active_hart_mask=0b11,in_qemu_mode=True -Ddiag_attributes_yaml=<ATTRIBUTES> -Ddiag_sources=<SOURCES> -Ddiag_name=<NAME>
```

### Running diags in M/S/U modes

Jumpstart will initialize the system and jump to the diag `main()`.

By default, `main()` will be called in S-mode. To enter `main()` in M-mode, set the `start_test_in_machine_mode` attribute to `True` in the Attribute file (See [test009's Attribute File](tests/test009.test_attributes.yaml) for an example).

Diags can use the `run_function_in_supervisor_mode()` and `run_function_in_user_mode()` functions to run functions in supervisor and user mode respectively. Machine, Supervisor and User mode cannot share code sections so the code for different modes have to be separated using the `mappings` attribute and by tagging the functions with the names of the corresponding sections.
Refer to the Unit Tests `test002`, `test011` (Run in User Mode) and `test018` (Run in Supervisor Mode) for examples of how these functions can be called and how the memory map can be set up.

### MP diags

The active harts in a diag are indicated by setting the `active_hart_mask` test attribute.

```
active_hart_mask: "0b1111"
```

**NOTE: Spike takes the number of active cores and not a bitmask so a diag built with non-consecutive harts enabled in the `active_hart_mask` mask cannot be run on Spike.**

**NOTE: The UART APIs are not multi-hart safe. Only one hart should write to the UART at a time.**


### Building Diags

Pass the sources and the attribute file to `meson setup` with the `-Ddiag_attributes_yaml`, `-Ddiag_name` and `-Ddiag_sources` build flags:


```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attributes_yaml=<PATH_TO_TEST_ATTRIBUTES_YAML> -Ddiag_sources=<COMMA SEPARATED LIST OF SOURCE FILES> -Ddiag_name=<DIAG NAME>
meson compile -C builddir
```

Example:
```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attributes_yaml=`pwd`/tests/test000.diag_attributes.yaml -Ddiag_sources=`pwd`/tests/test000.c -Ddiag_name=my_jumpstart_diag
meson compile -C builddir
```

This will build `builddir/my_jumpstart_diag`

To run the generated diag on Spike, use the `meson test` option.

### Miscellaneous debugging help

If the diag requires additional arguments be passed to Spike, these can be specified at setup time with `-Dspike_additional_arguments`.

For example, to pass the options:

* `-p2`: Run 2 harts

to spike when running a generated diag:

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attributes_yaml=`pwd`/tests/test013.diag_attributes.yaml -Ddiag_sources=`pwd`/tests/test013.c -Ddiag_attribute_overrides=active_hart_mask=0b11 -Dspike_additional_arguments=-p2
meson compile -C builddir
meson test -C builddir -v
```

#### Generating the trace

The execution traces can be obtained in one of the following additional arguments during setup time:

* -Dspike_additional_arguments=-v1 --log-commits
* -Dspike_generate_trace=true

#### Interactive debugging

The meson test doesn't support spike's command line debugging facility for interactive debugging.
However, the spike can be run manually with `-d` for interactive debugging.

```
meson setup builddir --cross-file cross-file.txt --buildtype release -Ddiag_attributes_yaml=`pwd`/tests/test006.diag_attributes.yaml -Ddiag_sources=`pwd`/tests/test006.c -Dspike_additional_arguments=-d
meson compile -C builddir
meson test -C builddir

#Extract the spike command line from the log file and fix the diag path correctly
spike --pass-fail --isa=rv64gchv_zba_zbb_zbc_zbs_zbkb_sstc_svpbmt_svinval_sscofpmf_zicbom_zicbop_zicboz_zfh_zfhmin_zfbfmin_zvfh_zvfhmin_zvfbfmin_\
zvfbfwma_zkt_zkr_zicsr_zifencei_zihintpause_zawrs_zicond_zvkned_zvbb_zvkg_zvknha_zvknhb_zvksh_zvksed_xrivostime_xrivospagewalk_xrivoscode_smaia_ssaia -d builddir/jumpstart_diag.elf
```
## Support

For help, please send a message on the Slack channel #jumpstart-directed-diags-framework.
