# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

common_jumpstart_tests = [
  # 0. prefix
  # 1. description
  # 2. expected to fail
  # 3. spike additional arguments
  # 4. disable on QEMU
  # 5. disable on spike
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.', false, '', true, false],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.', false, '', true, false],
  ['test002', 'Run C/Assembly functions with run_function_in_user_mode() from supervisor mode.', false, '', true, false],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.', false, '', true, false],
  ['test006', 'Read and Write CSRs.', false, '', true, false],
  ['test009', 'Jump to main() in machine mode and exit.', false, '', true, false],
  ['test011', 'Handle user mode exceptions in supervisor mode.', false, '', true, false],
  ['test012', 'Exit with DIAG_FAILED to test fail path', true, '', true, false],
  ['test013', 'test000 with 4 harts.', false, '-p4', false, false],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', true, '-p4', false, false],
  ['test017', 'Register and run Machine mode illegal instruction exception handler.', false, '', true, false],
  ['test018', 'Run C/Assembly functions with run_function_in_supervisor_mode() from machine mode.', false, '', true, false],
  ['test019', 'Sync 4P CPUs.', false, '-p4', false, false],
  ['test020', 'translate_VA() and page table modification test.', false, '', true, false],
  ['test021', '2P translate_VA() and page table modification test.', false, '-p2', true, false],
  ['test022', 'Exit with jumpstart_supervisor_fail() to test fail path.', true, '', true, false],
  ['test023', 'Handle S mode exceptions in M mode handlers.', false, '', true, false],
  ['test026', 'VA != PA mapping.', false, '', true, false],
  ['test027', 'VA aliasing test.', false, '', true, false],
  ['test028', 'Super Pages (SATP.mode = sv39) VA translation test.', false, '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x2000,0xC0022000:0x1000,0xD0000000:0x400000,0xE0000000:0x400000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000', false, false],
  ['test029', 'Super Pages (SATP.mode = sv48) VA translation test.', false, '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x2000,0xC0022000:0x1000,0xD0000000:0x400000,0xE0000000:0x400000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000', false, false],
  ['test030', 'Heap malloc test.', false, '', false, false],
  ['test031', 'Simple spinlock test with 4 harts', false, '-p4', false, false],
]
