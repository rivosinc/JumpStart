<!--
SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Reference Manual

JumpStart provides a bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

A Diag is expected to provide sources (C and assembly files) and it's attributes in a YAML file.

The JumpStart [`Unit Tests`](../tests) are a good reference on writing diags:
* [Common tests](../tests/common/meson.build)

**For a Quick Start Guide, see [Anatomy of a Diag](quick_start_anatomy_of_a_diag.md)** which provides a detailed explanation of `test021` which is a 2-core diag that modifies a shared page table in memory and checks that the change is visible to both cores.

## Diag Sources

Diags are written in C and/or Assembly.

The diag sources are required to contain a `main()` function which is the entry point for the diag that JumpStart jumps to. The linker will automatically place diag code (including `main()`) in the `.text` section. JumpStart expects that the `main()` function is always in the `.text` section. A [mapping](#mappings) for the `.text` section should be present in the diag's [attribute file](#diag-attributes).

Machine, Supervisor and User mode cannot share code so the code for different modes have to be placed in different linker sections. The [`linker_script_section`](#linker_script_section) in the [`mappings`](#mappings) diag attribute should be used by the diag to place the code for different modes in different sections.

JumpStart provides a set of basic API functions that the diag can use. Details [HERE](#jumpstart-apis).

The diag exits by returning from `main()` with a `DIAG_PASSED` or `DIAG_FAILED` return code. Alternatively, the diag can call `jumpstart_mmode_fail()` or `jumpstart_smode_fail()` functions if a clean return from `main()` is not possible. On return from the diag, JumpStart will exit the simulation with the appropriate exit code and exit sequence for the simulation environment.

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

**The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for JumpStart purposes and should not be used in diags.** TP is used to point to a per hart attributes structure and GP is used as a temporary in JumpStart routines.

## Diag Attributes

The Diag Attributes file specifies the memory layout and various attributes of the diag such as the MMU mode, number of active harts, etc.

The default diag attribute values are defined in the [Source Attributes YAML file](../src/public/jumpstart_public_source_attributes.yaml).

### `active_hart_mask`

Binary bitmask controlling how many active harts are in the diag. Any hart that is not part of the bitmask will be sent to `wfi`.

Default: `0b1` or 1 hart active.

Specifies the active harts in the diag. The default is `0b1` or 1 hart active.

### `enable_virtualization`

Enable the Virtualization extension.

Default: `False`.

### `satp_mode`, `vstap_mode`, `hgatp_mode`

The MMU mode (SV39, SV48, etc.) that will be programmed into the corresponding *ATP register.

### `start_test_in_mmode`

Controls whether the diag's `main()` will be called in M-mode or S-mode.

NOTE: Diags that run in `sbi_firmware_boot` mode (where JumpStart starts in S-mode after SBI Firmware runs) cannot start in M-mode.

Default: `False`. The diag's `main()` will be called in S-mode.

Example: [test009](../tests/common/test009.diag_attributes.yaml).

### `mmode_start_address`, `smode_start_address` and `umode_start_address`

The address at which the start of the Machine, Supervisor and User mode sections will be placed by the linker.

### `num_pages_for_jumpstart_smode_pagetables`

The maximum number of pages that can be used to allocate Page Tables.

### `num_pages_for_jumpstart_smode_bss` and `num_pages_for_jumpstart_smode_rodata`

The number of pages allowed for the `.bss` and `.rodata` sections respectively.

### `allow_page_table_modifications`

Allows the diag to modify the page tables.

Default: `False`. The page tables regions are marked Read Only in the page table map. This prevents accidental modification of the page tables from supervisor mode.

Example: [test021](../tests/common/test021.diag_attributes.yaml).

### `mappings`

Controls the memory layout and attributes of all the sections of the diag.

#### `va`, `gpa`, `pa`

Controls the virtual, guest physical and physical addresses of the mapping.

#### `stage`

Controls the translation stage (S, VS, G) that this mapping will be used in. The S stage is the single stage translation and the VS and G stages are the two stage translation.

Default: If not explicitly specified, the stage will be inferred based on the `va`, `gpa` and `pa` attributes. It will be set to `None` for a direct mapping (only the `pa` has been specified).

#### `xwr`, `umode` and `valid`

Controls the values of the `xwr`, `umode` and `valid` bits in the page table entry for the section.

#### `page_size`

Controls the page size of the section.

The page size has to conform to the sizes supported by the SATP mode.

#### `num_pages`

Controls the number of pages allocated for the section.

#### `alias`

Indicates whether this is a VA alias. It's PA should be contained in the PA range of another mapping.

#### `no_pte_allocation`

Controls whether the diag will allocate page table entries for the section.
If not explicitly specified, this will be inferred based on the translation stage. It will be set to `True` for direct mappings (`stage` is `None`) and `False` for non-direct mappings.

Default: `None`.

#### `linker_script_section`

The name of the linker script section that this section will be placed in.

Machine, Supervisor and User mode cannot share code so the code for different modes have to be placed in different linker sections.

This takes a comma separated list of all the sections that should be placed together. For example:

```yaml
linker_script_section: ".text,.text.end"
```

The sections `.text` and `.text.end` will be placed together in the `.text` linker script section - the name of the first section in the list is used as the linker script section name:

```Linker Script
   . = 0x80000000;
   .text : {
      *(.text)
      *(.text.end)
   }
```

## Building Diags

`meson` is used to build the diags. The diags are built in 2 stages - `meson setup` and `meson compile`.

### `meson setup`

Takes the diag's sources and attributes and generates a meson build directory.

Pass the sources and the attribute file to `meson setup` with the `diag_attributes_yaml`, `diag_name` and `diag_sources` setup options:

```shell
meson setup builddir --cross-file cross_compile/rivos_internal/gcc_options.txt --cross-file cross_compile/gcc.txt  --buildtype release -Ddiag_attributes_yaml=tests/common/test000.diag_attributes.yaml -Ddiag_sources=tests/common/test000.c -Ddiag_name=my_jumpstart_diag
```

All `meson setup` options are listed in the [meson_options.txt](../meson.options) file.

#### `diag_attribute_overrides`

Diag attributes specified in the diag's attribute file can be overriden at `meson setup` with the `diag_attribute_overrides` option. `diag_attribute_overrides` takes a list of attributes that can be overriden.

For example, to override the `active_hart_mask`:

```shell
meson setup builddir -Ddiag_attribute_overrides=active_hart_mask=0b11 ...
```

### `meson compile`

Compiles the diag for which the meson build directory has been generated by `meson setup`.

```shell
meson compile -C builddir
```

This will build `builddir/my_jumpstart_diag`

### `meson test`

Runs the generated diag in Spike.

```shell
meson test -C builddir
```

## JumpStart APIs

These are listed in the header files in the [include](../include) directory.

Functions with names that end in `_from_smode()` or `_from_mmode()` can only be called from the respective modes.

### `get_thread_attributes_hart_id_from_smode()`

Returns the hart id of the hart calling the function. Can only be called from S-mode.

### `read_csr()`, `write_csr()`, `read_write_csr()`, `set_csr()`, `clear_csr()`, `read_set_csr()` and `read_clear_csr()`

Operates on the specified CSR. The CSR names are passed to the RISC-V `csrr` and `csrw` instructions so the names should match what GCC expects.

### `run_function_in_smode()` and `run_function_in_umode()`

Diags can use the `run_function_in_smode()` and `run_function_in_umode()` functions to run functions in supervisor and user mode respectively. Each function can be passed up to 6 arguments.

The different modes cannot share the same pages so the functions belonging to each mode should be tagged with the corresponding linker script section name to place them in different sections.

Refer to Unit Tests `test002`, `test011` and `test018` for examples of how these functions can be called and how the memory map can be set up.

### `disable_mmu_from_smode()`

Disables the MMU. The page tables are set up and the MMU is enabled by default when the diag starts.

### `sync_all_harts_from_smode()`

Synchronization point for all active harts in the diag.

### `register_mmode_trap_handler_override()` and `get_mmode_trap_handler_override()`

Allows the diag to register a trap handler override function for M-mode traps. The registered function will be called when the trap occurs in M-mode.

### `register_smode_trap_handler_override()` and `get_smode_trap_handler_override()`

Allows the diag to register a trap handler override function for S-mode traps. The registered function will be called when the trap occurs in S-mode.

### `get_*epc_for_current_exception()` and `set_*epc_for_current_exception()`

These functions can be used to get and set the MEPC/SEPC during an exception. Allows modification of the EPC before returning from the exception.

## Running Diags

JumpStart diags can be run on Spike and QEMU targets.

The target can be specified by passing the `-Dtarget` option to `meson setup`. The target can be `spike` or `qemu`.

`meson test` will attempt to run the diag on the target. To see the options being passed to the target, run `meson test` with the `-v` option.

```shell
meson test -C builddir -v
```

To generate the execution trace, pass the `generate_trace=true` option to `meson setup`.

```shell
meson setup -C builddir -Dgenerate_trace=true ...
```

If the diag requires additional arguments be passed to the target, specify them with the `spike_additional_arguments`/`qemu_additional_arguments` options to `meson setup`.
These take a list of arguments.

```shell
meson setup -C builddir -Dspike_additional_arguments=-p2 ...
```
## Boot Configs

The boot path can be selected at build time with the `boot_config` meson option.

### `fw-none` (default)

   JumpStart starts running from hardware reset. No system firmware is expected to be present.

### `fw-m`

JumpStart starts in M-mode at the `mmode_start_address` after running system firmware for initialization. The system firmware that runs prior to JumpStart can be overwritten by JumpStart.

### `fw-sbi`

JumpStart starts in S-mode at the `sbi_firmware_trampoline` address after running system firmware for initialization. The system firmware is expected to be resident and will not be overwritten by JumpStart. JumpStart will interact with the system firmware using the SBI HSM extension - for example, to boot non-booting harts.

Only S-mode based diags can be run in this mode as JumpStart cannot enter M-mode.
