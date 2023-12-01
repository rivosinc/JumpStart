# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

common_jumpstart_tests = [
  # 0. prefix
  # 1. description
  # 2. expected to fail
  # 3. spike additional arguments
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.', false, ''],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.', false, ''],
  ['test002', 'Run C/Assembly functions with run_function_in_user_mode() from supervisor mode.', false, ''],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.', false, ''],
  ['test006', 'Read and Write CSRs.', false, ''],
  ['test009', 'Jump to main() in machine mode and exit.', false, ''],
  ['test011', 'Handle user mode exceptions in supervisor mode.', false, ''],
  ['test012', 'Exit with DIAG_FAILED to test fail path', true, ''],
  ['test013', 'test000 with 4 harts.', false, '-p4'],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', true, '-p3'],
  ['test017', 'Register and run Machine mode illegal instruction exception handler.', false, ''],
  ['test018', 'Run C/Assembly functions with run_function_in_supervisor_mode() from machine mode.', false, ''],
  ['test019', 'Sync 4P CPUs.', false, '-p4'],
  ['test020', 'translate_VA() and page table modification test.', false, ''],
  ['test021', '2P translate_VA() and page table modification test.', false, '-p2'],
  ['test022', 'Exit with jumpstart_supervisor_fail() to test fail path.', true, ''],
  ['test023', 'Handle S mode exceptions in M mode handlers.', false, ''],
  ['test026', 'VA != PA mapping.', false, ''],
  ['test027', 'VA aliasing test.', false, ''],
]
