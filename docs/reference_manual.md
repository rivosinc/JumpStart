<!--
SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Reference Manual

JumpStart provides a bare-metal kernel, APIs and build infrastructure for writing directed diags for RISC-V CPU/SoC validation.

A Diag is expected to provide sources (C and assembly files) and it's attributes in a YAML file.

The JumpStart [`Unit Tests`](../tests) are a good reference on writing diags:
* [Common tests](../tests/common/meson.build)

**For a Quick Start Guide, see [Anatomy of a Diag](quick_start_anatomy_of_a_diag.md)** which provides a detailed explanation of `test021` which is a 2-core diag that modifies a shared page table in memory and checks that the change is visible to both cores.

## Table of Contents

* [Diag Sources](#diag-sources)
* [Diag Attributes](#diag-attributes)
* [JumpStart APIs](#jumpstart-apis)
* [Building and Running Diags](#building-and-running-diags)

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

The MMU mode that will be programmed into the corresponding *ATP register.

Valid values: `bare`, `sv39`, `sv48`, `sv39x4`, `sv48x4`.

### `start_test_in_mmode`

Controls whether the diag's `main()` will be called in M-mode or S-mode.

Default: `False`. The diag's `main()` will be called in S-mode.

Example: [test009](../tests/common/test009.diag_attributes.yaml).

### `mmode_start_address`, `smode_start_address` and `umode_start_address`

The address at which the start of the Machine, Supervisor and User mode sections will be placed by the linker.

### `max_num_pagetable_pages_per_stage`

The maximum number of 4K pages that can be used to allocate Page Tables for each translation stage.

### `num_pages_for_jumpstart_smode_bss` and `num_pages_for_jumpstart_smode_rodata`

The number of 4K pages allowed for the `.bss` and `.rodata` sections respectively.

### `allow_page_table_modifications`

Allows the diag to modify the page tables.

Default: `False`. The page tables regions are marked Read Only in the page table map. This prevents accidental modification of the page tables from supervisor mode.

Example: [test021](../tests/common/test021.diag_attributes.yaml).

### `mappings`

Controls the memory layout and attributes of all the sections of the diag.

#### `va`, `gpa`, `pa`, `spa`

Controls the virtual, guest physical, physical and supervisor physical addresses of the mapping.

#### `stage`

Controls the translation stage (S, VS, G) that this mapping will be used in. The S stage is the single stage translation and the VS and G stages are the two stage translation.

Default: If not explicitly specified, the stage will be inferred based on the `va`, `gpa`, `pa`, `spa` attributes. A bare mapping will only have a `gpa`, `pa` or a `spa` attribute.

#### `xwr`, `umode` and `valid`

Controls the values of the `xwr`, `umode` and `valid` bits in the page table entry for the section.

#### `page_size`

Controls the page size of the section.

The page size has to conform to the sizes supported by the SATP mode.

#### `num_pages`

Controls the number of `page_size` pages allocated for the section.

#### `alias`

Indicates whether this is a VA alias. It's PA should be contained in the PA range of another mapping.

#### `no_pte_allocation`

Controls whether the diag will allocate page table entries for the section.
If not explicitly specified, this will be inferred based on the translation stage. It will be set to `True` for bare mappings and `False` for non-bare mappings.

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

## Building and Running Diags

`meson` is the underlying build flow used to build the diags. Both the [`scripts/build_diag.py`](#scriptsbuild_diagpy) and the `justfile` wrap the meson build system.

### `scripts/build_diag.py`

The preferred way to build and run using JumpStart is to use the [`scripts/build_diag.py`](../scripts/build_diag.py) script.

The script takes as input a diag source directory containing the diag's sources and attributes file, the toolchain to be used and the target to run the diag on.

Run `--help` for all options.

#### `--override_meson_options`

Used to override the meson options specified in [meson.options](../meson.options).

#### `--override_diag_attributes`

Used to override the diag attributes specified in the [attributes file](../src/public/jumpstart_public_source_attributes.yaml). This will override the attributes specified in the diag's attributes file.

### `justfile`

This provides a way to build and test the unit tests during development.

Run `just --list` to see all the available commands.

Examples:

```shell
# Build all unit tests with GCC targeting release build and run on Spike.
just gcc release spike
```

## JumpStart APIs

These are listed in the header files in the [include](../include) directory.

Functions with names that end in `_from_smode()` or `_from_mmode()` can only be called from the respective modes.

### Memory Management APIs

JumpStart provides a heap-based memory management system that supports allocations from DDR memory with different memory attributes (WB, WC, UC). A DDR WB heap is set up by default, but other heaps must be explicitly initialized before use.

#### Basic Memory Functions
- `malloc()`, `free()`, `calloc()`, `memalign()`: Default memory allocation functions that use DDR WB memory.

#### Memory Type Specific Functions
- `malloc_from_memory()`, `free_from_memory()`, `calloc_from_memory()`, `memalign_from_memory()`: Memory allocation functions that allow specifying the backing memory and memory type.

#### Heap Management
- `setup_heap()`: Initialize a new heap with specified backing memory and memory type.
- `deregister_heap()`: Clean up and remove a previously initialized heap.
- `get_heap_size()`: Get the total size of a specific heap.

The following constants are defined for use with these functions:

**Backing Memory Types:**
- `BACKING_MEMORY_DDR`: Standard DDR memory

**Memory Types:**
- `MEMORY_TYPE_WB`: Write-Back cached memory
- `MEMORY_TYPE_WC`: Write-Combining memory
- `MEMORY_TYPE_UC`: Uncached memory

Example usage:
```c
// Set up a 4MB uncached DDR heap
setup_heap(0xA0200000, 0xA0200000 + 4 * 1024 * 1024,
          BACKING_MEMORY_DDR, MEMORY_TYPE_UC);

// Allocate from the uncached heap
void* buf = malloc_from_memory(size, BACKING_MEMORY_DDR, MEMORY_TYPE_UC);

// Clean up when done
free_from_memory(buf, BACKING_MEMORY_DDR, MEMORY_TYPE_UC);
deregister_heap(BACKING_MEMORY_DDR, MEMORY_TYPE_UC);
```

### `get_thread_attributes_hart_id_from_smode()`

Returns the hart id of the hart calling the function. Can only be called from S-mode.

### `read_csr()`, `write_csr()`, `read_write_csr()`, `set_csr()`, `clear_csr()`, `read_set_csr()` and `read_clear_csr()`

Operates on the specified CSR. The CSR names are passed to the RISC-V `csrr` and `csrw` instructions so the names should match what GCC expects.

### `run_function_in_smode()`, `run_function_in_umode()`, `run_function_in_vsmode()` and `run_function_in_vumode()`

Diags can use these functions to run functions in the corresponding modes. Each function can be passed up to 6 arguments.

`run_function_in_smode()` can only be called from M-mode.

`run_function_in_umode()` and `run_function_in_vsmode()` can only be called from S-mode.

`run_function_in_vumode()` can only be called from VS-mode.

The different modes cannot share the same pages so the functions belonging to each mode should be tagged with the corresponding linker script section name to place them in different sections.

*IMPORTANT*: The return values of these functions should be checked. The only way to tell if the function ran successfully is to check the return value.

Refer to Unit Tests `test002`, `test011`, `test018`, `test045`, `test048` for examples of how these functions can be called and how the memory map can be set up.

### `disable_mmu_from_smode()`

Disables the MMU. The page tables are set up and the MMU is enabled by default when the diag starts.

### `sync_all_harts_from_smode()`

Synchronization point for all active harts in the diag.

### `register_mmode_trap_handler_override()` and `get_mmode_trap_handler_override()`

Allows the diag to register a trap handler override function for M-mode traps. The registered function will be called when the trap occurs in M-mode.

### `register_smode_trap_handler_override()` and `get_smode_trap_handler_override()`

Allows the diag to register a trap handler override function for S-mode traps. The registered function will be called when the trap occurs in S-mode.

### `register_vsmode_trap_handler_override()` and `get_vsmode_trap_handler_override()`

Allows the diag to register a trap handler override function for VS-mode traps. The registered function will be called when the trap occurs in VS-mode.

### `get_*epc_for_current_exception()` and `set_*epc_for_current_exception()`

These functions can be used to get and set the MEPC/SEPC during an exception. Allows modification of the EPC before returning from the exception.
