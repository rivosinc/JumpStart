# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

  .section .text.prologue, "ax"
  # special section just for the _start label

  .align 2
  .globl _start
  .type _start, @function
_start:

  nop
  nop
  nop
  nop
  nop
  nop
  nop
  nop

  la      sp, stack_bottom


  # jump and link to _main
  jal main

  lui x0, 0xdeadb

  nop
  ret

  .text

  .align 2
  .globl asm_func
  .type asm_func, @function
asm_func:

  nop
  ret

# From:
# https://community.arm.com/arm-community-blogs/b/architectures-and-processors-blog/posts/useful-assembler-directives-and-macros-for-the-gnu-assembler
# The .size directive can be used to tell the assembler how much space the data that a symbol points to is using.
# For instance...
#                    .size               qsort,.-qsort
# will calculate the total size in bytes of the function 'qsort', so that the linker can exclude the function if it's unused.
  .size asm_func, .-asm_func

  .section .data

  .globl stack_top
stack_top:
  .skip 0x1000
  .globl stack_bottom
stack_bottom:
