<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# FAQs

## Are there restrictions on what GPRs I can use in my diags?

**Yes.** The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for jumpstart purposes and should not be used in diags. TP is used to point to a per hart attributes structure and GP is used as a temporary in jumpstart routines.

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

## I'm unable to run spike in interactive debugging mode with `meson test`.

Running spike through `meson test` breaks spike's command line debugging facility (`-d`) for interactive debugging.

You will need to run spike manually with `-d` for interactive debugging.
