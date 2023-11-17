# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

common_jumpstart_tests = [
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.'],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.'],
  ['test002', 'Run C/Assembly functions with run_function_in_user_mode() from supervisor mode.'],
  ['test003', 'Register and run Supervisor mode illegal instruction exception handler.'],
  ['test006', 'Read and Write CSRs.'],
  ['test009', 'Jump to main() in machine mode and exit.'],
  ['test011', 'Handle user mode exceptions in supervisor mode.'],
  ['test012', 'Exit with DIAG_FAILED to test fail path.', '', true],
  ['test013', 'test000 with 4 harts.', '-p4'],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', '-p3', true],
  ['test017', 'Register and run Machine mode illegal instruction exception handler.'],
  ['test018', 'Run C/Assembly functions with run_function_in_supervisor_mode() from machine mode.'],
  ['test019', 'Sync 4P CPUs.', '-p4'],
  ['test020', 'translate_VA() and page table modification test.'],
  ['test021', '2P translate_VA() and page table modification test.', '-p2'],
  ['test022', 'Exit with jumpstart_supervisor_fail() to test fail path.', '', true],
  ['test023', 'Handle S mode exceptions in M mode handlers.'],
  ['test026', 'VA != PA mapping.'],
]
