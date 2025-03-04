# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

fs = import('fs')

source_suffixes = ['.S', '.c']

# 0. prefix
# 1. description
# 2. spike additional arguments
# 3. expected to fail
start_in_smode_tests += [
  ['test000', 'Enable MMU (SATP.mode = sv39), jump to main and exit.'],
  ['test001', 'Enable MMU (SATP.mode = sv48), jump to main and exit.'],
  ['test002', 'Run C/Assembly functions with run_function_in_umode() from supervisor mode.'],
  ['test003', 'Register and run smode illegal instruction exception handler.'],
  ['test006', 'Read and Write CSRs.'],
  ['test010', 'ELF checks.'],
  ['test011', 'Handle user mode exceptions in supervisor mode.'],
  ['test012', 'Exit with DIAG_FAILED to test fail path', '', true],
  ['test013', 'test000 with 4 harts.', '-p4'],
  ['test014', 'Hart 2 exits with DIAG_FAILED to test MP fail path.', '-p4', true],
  ['test019', 'Sync 4P CPUs.', '-p4'],
  ['test020', 'translate_VA() and page table modification test.'],
  ['test021', '2P translate_VA() and page table modification test.', '-p2', false],
  ['test022', 'Exit with jumpstart_smode_fail() to test fail path.', '', true],
  ['test026', 'VA != PA mapping.'],
  ['test027', 'sv39 VA aliasing test.'],
  ['test028', 'Super Pages (SATP.mode = sv39) VA translation test.', '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x4000,0xD0000000:0x400000,0xE0000000:0x401000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000'],
  ['test029', 'Super Pages (SATP.mode = sv48) VA translation test.', '-m0x80000000:0x40000000,0xC0000000:0x1000,0xC0020000:0x4000,0xD0000000:0x400000,0xE0000000:0x401000,0xD0400000:0x200000,0x100000000:0x4000000,0x140000000:0x40000000'],
  ['test030', 'Heap malloc test.'],
  ['test031', 'Simple spinlock test with 4 harts', '-p4'],
  ['test033', 'Exit with jumpstart_umode_fail() to test umode fail path.', '', true],
  ['test034', 'Simple spinlock test with 4 active harts and 4 inactive ones.', '-p8'],
  ['test036', 'sv48 VA aliasing test.'],
  ['test037', 'FP/Vector test.'],
  ['test039', 'MP heap malloc test.', '-p4'],
  ['test045', 'Run C/Assembly functions with run_function_in_vsmode() from supervisor mode.'],
  ['test046', 'Register and run vsmode illegal instruction exception handler.', '-p4'],
  ['test047', 'Hypervisor load/store.'],
  ['test048', 'Run C/Assembly functions with run_function_in_vumode() from VS mode.'],
  ['test049', 'Exit with jumpstart_vumode_fail() to test umode fail path.', '', true],
  ['test050', 'Exit with jumpstart_vsmode_fail() to test fail path.', '', true],
  ['test051', 'MMU with SATP.mode = bare.'],
  ['test052', 'Test string.h functions.'],
  ['test053', 'Test time() and gettimeofday().'],
  ['test058', 'Run cores 1 and 3 with cores 0 and 2 marked as inactive.', '-p4'],
]

start_in_mmode_tests += [
  ['test009', 'Jump to main() in machine mode and exit.'],
  ['test017', 'Register and run Machine mode illegal instruction exception handler.'],
  ['test018', 'Run C/Assembly functions with run_function_in_smode() from machine mode.'],
  ['test023', 'Handle S mode exceptions in M mode handlers.'],
  ['test038', '2P where only non-primary hart runs functions with run_functions_in_smode().', '-p2'],
  ['test040', 'Run smode function during mmode exception handler.'],
  ['test041', 'Fail gracefully on hitting too many nested exceptions in smode.', '', true],
  ['test042', 'Run Supervisor mode illegal instruction exception handler on 4 cores.', '-p4'],
  ['test044', 'Tests random number generation and seed csr from both M and S modes.', '-p4'],
]

tests_disabled_on_qemu += []
tests_disabled_on_spike += []
