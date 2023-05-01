/*
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only
*/

OUTPUT_ARCH( "riscv" )
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;

  /* Place special section .text.prologue before everything else */
  .text : {
    *(.text.prologue);
    *(.text);
  }

  .data : { *(.data) }

  .rodata : { *(.rodata*); }

  .bss : { *(.bss) }

  _end = .;
}
