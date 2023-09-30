<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# FAQs

## Are there restrictions on what GPRs I can use in my diags?

**Yes.** The Thread Pointer (x4) and Global Pointer (x3) registers are reserved for JumpStart purposes and should not be used in diags. TP is used to point to a per hart attributes structure and GP is used as a temporary in JumpStart routines.

**Diags are expected to follow the [RISC-V ABI Calling Convention](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc).**

## I'm unable to run spike in interactive debugging mode with `meson test`.

Running spike through `meson test` breaks spike's command line debugging facility (`-d`) for interactive debugging.

You will need to run spike manually with `-d` for interactive debugging.

# Rivos Internal FAQs

## I want checkTC to compare the spike and RTL traces for an multi-core run. Is there a way I can disable the comparisons for sections of the diag that I know will mismatch such as a sync routine?

Yes, you can use the CHECKTC_DISABLE and CHECKTC_ENABLE macros to disable and enable the checkTC comparisons. These inject magic instructions that tell checkTC to disable/enable comparisons between the Spike and RTL traces.
