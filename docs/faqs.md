<!--
SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# FAQs

## Are there restrictions on what GPRs I can use in my diags?

**Yes.** The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for JumpStart purposes and should not be used in diags. TP is used to point to a per cpu attributes structure and GP is used as a temporary in JumpStart routines.

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

## I'm unable to run spike in interactive debugging mode with `meson test`.

Running spike through `meson test` breaks spike's command line debugging facility (`-d`) for interactive debugging.

You will need to run spike manually with `-d` for interactive debugging.

## What's the best way to debug a diag that is behaving incorrectly?

* If your diag can run on Spike, generate the spike trace and see where things go off the rails.
  * Look for `trap` to find unexpected exceptions.
  * Look for the point where your code returns to the JumpStart code.
  * Run spike with the `-d` flag to step through your diag and inspect registers and memory.
* Build with the `--buildtype debug` to turn off optimizations and generate debug information. The disassembly generated will have your code interleaved with the assembly, making it easier to correlate the two.
