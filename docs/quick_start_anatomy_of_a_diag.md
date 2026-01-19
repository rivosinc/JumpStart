<!--
SPDX-FileCopyrightText: 2023 - 2026 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# Quick Start: Anatomy of a Diag

`test021` is a 2P diag that has `CPU0` update the page table mapping of a page in memory by changing the valid bit from `0` to `1`. `CPU1` reads from the page before and after the valid bit is set to `1`. The test verifies that the read from `CPU1` fails when the valid bit is `0` and eventually succeeds after the valid bit is set to `1`.

The diag comprises of 2 source files:
* [`test021.c`](../tests/common/test021/test021.c)
* [`test021.S`](../tests/common/test021/test021.S)

and a diag attributes file:
* [`test021.diag_attributes.yaml`](../tests/common/test021/test021.diag_attributes.yaml)

## Diag Attributes YAML file

[`test021.diag_attributes.yaml`](../tests/common/test021/test021.diag_attributes.yaml) contains attributes that describe the diag. JumpStart uses these attributes to generate diag specific code, data structures and files.

```yaml
active_cpu_mask: "0b11"
```
This is a 2P diag with CPUs 0 and 1 active. JumpStart will allocate enough space in data structures for 2 CPUs. Any CPUs not specified in the active_cpu_mask will be considered inactive and sent to wfi if encountered.

```yaml
satp_mode: "sv39"
```
JumpStart will generate MMU setup functions to program the `sv39` mode into the `SATP` CSR as well as generate the page tables for `sv39` mode.

```yaml
allow_page_table_modifications: true
```
Page tables are read-only by default - the page table entries for the page table area are only assigned `R` permissions.

This attribute tells JumpStart that the diag will be modifying the page tables so JumpStart will additionally add the `W` permission to the page table entries for the page table area.


```yaml
mappings:
  -
    va: 0x80000000
    pa: 0x80000000
    xwr: "0b101"
    page_size: 0x1000
    num_pages: 2
    pma_memory_type: "wb"
    linker_script_section: ".text"
  -
    va: 0x80004000
    pa: 0x80004000
    xwr: "0b101"
    page_size: 0x1000
    num_pages: 1
    pma_memory_type: "wb"
    linker_script_section: ".data"
  -
    va: 0x80006000
    pa: 0x80006000
    xwr: "0b101"
    valid: "0b0"
    page_size: 0x1000
    num_pages: 1
    pma_memory_type: "wb"
    linker_script_section: ".data.diag"
```

The `mappings` attribute describes the layout of the diag sections in memory along with the permissions, size, name etc. of each section.

By default, the compiler will place all C code in the `.text` section and all C global variables in the `.data` section.

Based on the `mappings` specified for this diag, JumpStart will generate a linker script that places the `.text` section at Physical Address `0x80000000` and the `.data` section at Physical Address  `0x80004000`. This linker script is passed to the compiler to generate the diag ELF.

The `.text` section is 2 pages long and as `RX` (Read-Execute) permissions along with the `wb` (writeback) memory type. The page tables entries generated for the `.text` section are marked as `RX` (read-execute).

The `.data` section is 1 page long and has RW permissions along with the `wb` memory type. The page table entries generated for the `.data` section are marked as `RW` (read-write).

The diag additionally defines a `.data.diag` section at `0x80006000`. The `valid` attribute for this section is set to `0b0` - JumpStart will set up the page tables for this section but set the valid bit in it's it's leaf (last level) page table entry to `0`.

## Source Files

By default, the JumptStart boot code will start in machine mode, initialize the system (MMU, interrupts, exception handling etc) and then jump to the diag's `main` function in Supervisor mode.

[`test021.c`](../tests/common/test021/test021.c) contains `main()` that the JumpStart boot code will jump to after initializing the system.

```c
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();
  if (cpu_id > 1) {
    return DIAG_FAILED;
  }
```

It reads out the CPU id and checks that only CPU 0 or 1 is running the diag.

```c
  struct translation_info xlate_info;
  translate_VA(data_area_address, &xlate_info);
```

The diag calls `translate_VA()` to get the page table details for the VA of the `data_area` variable. JumpStart provides the `translate_VA()` function that returns a `struct translation_info` object that details of a table walk for a given `VA`:

```c
struct translation_info {
  uint8_t satp_mode;
  uint8_t levels_traversed;
  uint8_t walk_successful;
  uint64_t va;
  uint64_t pa;
  uint64_t pte_address[MAX_NUM_PAGE_TABLE_LEVELS];
  uint64_t pte_value[MAX_NUM_PAGE_TABLE_LEVELS];
};
```

The `data_area` variable is a global variable defined in the `.data.diag` section by [`test021.S`](../tests/common/test021/test021.S):

```asm
.section .data.diag, "wa", @progbits
.global data_area
data_area:
  .8byte MAGIC_VALUE
```

```c
  if (xlate_info.walk_successful != 0 || xlate_info.levels_traversed != 3 ||
      (xlate_info.pte_value[2] & PTE_V) != 0) {
    return DIAG_FAILED;
  }
```

The diag sanity checks that the valid bit is not set for the leaf page table entry for this translation. `walk_successful` will be `0` as the translation encountered the invalid leaf page table entry but `levels_traversed` will be `3` as it would have traversed 3 levels to get to the leaf page table entry.

```c
  if (cpu_id == 1) {
    register_smode_trap_handler_override(
        SCAUSE_EC_LOAD_PAGE_FAULT, (uint64_t)(&cpu1_load_page_fault_handler));
..
..
```

CPU1 registers a supervisor mode trap handler override (`cpu1_load_page_fault_handler()`) for the load page fault exception using the `register_smode_trap_handler_override()` API provided by JumpStart.

```c
    if (is_load_allowed_to_data_area() == 1) {
      return DIAG_FAILED;
    }
```

`CPU1` calls `is_load_allowed_to_data_area()` to check that the reads to the data area are not allowed.

`is_load_allowed_to_data_area()` is defined in [`test021.S`](../tests/common/test021/test021.S):

```asm
.section .text, "ax", @progbits
.global is_load_allowed_to_data_area
is_load_allowed_to_data_area:
..
..
  la t0, data_area

  li t1, 0
  # This access will fault if the PTE has not been marked as valid.
  # The fault handler will just skip over this instruction.
  ld t1, 0(t0)

  li t2, MAGIC_VALUE
  bne t2, t1, access_faulted
..
..
```
`is_load_allowed_to_data_area()` issues a load to the `data_area` variable and returns `1` if the load succeeds. If the load faults, the load page fault exception handler `cpu1_load_page_fault_handler()` simply skips over the faulting instruction:

```c
void cpu1_load_page_fault_handler(void) {
..
..
  // skip over the faulting load
  uint64_t sepc_value = get_sepc_for_current_exception();
  set_sepc_for_current_exception(sepc_value + 4);
}
```

```c
  sync_all_cpus_from_smode();
```

The diag syncs up the cores so that they both complete all the above steps before `CPU0` modifies the page table entry to mark it as valid.

```c
  if (cpu_id == 0) {
    *((uint64_t *)xlate_info.pte_address[2]) =
        xlate_info.pte_value[2] | PTE_V;
    asm volatile("sfence.vma");
```

`CPU0` then marks the leaf page table entry for the `data_area` variable as valid and issues an `sfence.vma` to ensure that the page table entry is visible to all cores.

```c
    while (1) {
      translate_VA(data_area_address, &xlate_info);

      if (xlate_info.walk_successful == 1) {
        // The new PTE is now valid, so the load should succeed.
        if (is_load_allowed_to_data_area() == 0) {
          return DIAG_FAILED;
        }
        break;
      }
    }
```

`CPU1` will loop till it sees that the page table entry for the `data_area` variable is valid and then call `is_load_allowed_to_data_area()` to check that the reads to the data area are now allowed.

The diag returns with `DIAG_PASSED` or `DIAG_FAILED` and the JumpStart code will sync up the cores and then run the end of sim code.
