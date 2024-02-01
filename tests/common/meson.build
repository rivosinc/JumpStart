# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

common_jumpstart_tests = [
  # 0. prefix
  # 1. description
  # 2. spike additional arguments
  # 3. expected to fail
  # 4. disable on QEMU
  # 5. disable on spike
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.', '', false, true],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.', '', false, true],
  ['test002', 'Run C/Assembly functions with run_function_in_umode() from supervisor mode.', '', false, true],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.', '', false, true],
  ['test006', 'Read and Write CSRs.', '', false, true],
  ['test009', 'Jump to main() in machine mode and exit.', '', false, true],
  ['test010', 'Override default M-mode, S-mode, U-mode start address.', '', false, true],
  ['test011', 'Handle user mode exceptions in supervisor mode.', '', false, true],
  ['test012', 'Exit with DIAG_FAILED to test fail path', '', true, true],
  ['test013', 'test000 with 4 harts.', '-p4'],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', '-p4', true],
  ['test017', 'Register and run Machine mode illegal instruction exception handler.', '', false, true],
  ['test018', 'Run C/Assembly functions with run_function_in_smode() from machine mode.', '', false, true],
  ['test019', 'Sync 4P CPUs.', '-p4'],
  ['test020', 'translate_VA() and page table modification test.', '', false, true],
  ['test021', '2P translate_VA() and page table modification test.', '-p2', false, true],
  ['test022', 'Exit with jumpstart_smode_fail() to test fail path.', '', true, true],
  ['test023', 'Handle S mode exceptions in M mode handlers.', '', false, true],
  ['test026', 'VA != PA mapping.', '', false, true],
  ['test027', 'VA aliasing test.', '', false, true],
  ['test028', 'Super Pages (SATP.mode = sv39) VA translation test.', '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x2000,0xC0022000:0x1000,0xD0000000:0x400000,0xE0000000:0x400000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000'],
  ['test029', 'Super Pages (SATP.mode = sv48) VA translation test.', '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x2000,0xC0022000:0x1000,0xD0000000:0x400000,0xE0000000:0x400000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000'],
  ['test030', 'Heap malloc test.'],
  ['test031', 'Simple spinlock test with 4 harts', '-p4'],
  ['test033', 'Exit with jumpstart_umode_fail() to test umode fail path.', '', true, true],
]
