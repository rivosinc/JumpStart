// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"
#include "tablewalk_functions.supervisor.h"

extern uint64_t data_area;
extern uint64_t load_from_address(uint64_t address);

uint8_t PA_access_faulted = 0;

static void skip_instruction(void) {
  uint64_t reg = read_csr(sepc);

  uint32_t opcode = *((uint32_t *)reg);
  uint8_t instruction_size = 2;
  if ((opcode & 0x3) == 0x3) {
    instruction_size = 4;
  }

  /* Just skip the illegal instruction and move to next instruction. */
  write_csr(sepc, reg + instruction_size);

  PA_access_faulted = 1;
}

int main(void) {
  // The VA should map to the PA.
  const uint64_t VA = UINT64_C(0x80033000);
  const uint64_t PA = UINT64_C(0x80043000);
  uint64_t data_area_address = (uint64_t)&data_area;
  if (data_area_address != PA) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;
  translate_VA(VA, &xlate_info);
  if (xlate_info.walk_successful == 0) {
    return DIAG_FAILED;
  }
  if (xlate_info.pa != PA) {
    return DIAG_FAILED;
  }

  // This is the value initialized in assembly.
  const uint64_t magic_value = 0xcafecafecafecafe;

  // The linker script requires that the mappings are sorted by PA but the
  // PTE generation code requires that the mappings are sorted by VA.
  // This test has data.2 mapped to 0x80053000 and data.3 mapped to 0x80063000.
  // This will check that both these are functioning correctly.
  translate_VA(0x80053000, &xlate_info);
  if (xlate_info.pa != 0x80063000) {
    return DIAG_FAILED;
  }
  if (load_from_address(0x80053000) != (magic_value + 1)) {
    return DIAG_FAILED;
  }

  translate_VA(0x80063000, &xlate_info);
  if (xlate_info.pa != 0x80053000) {
    return DIAG_FAILED;
  }
  if (load_from_address(0x80063000) != (magic_value + 2)) {
    return DIAG_FAILED;
  }

  // This is the value we will write to the VA.
  uint64_t new_magic_value = UINT64_C(0xdeadbeefdeadbeef);

  uint64_t value_at_VA = load_from_address(VA);
  if (value_at_VA != magic_value) {
    return DIAG_FAILED;
  }

  *(uint64_t *)VA = new_magic_value;

  // An access to the PA should fault with the MMU on.
  register_supervisor_mode_trap_handler_override(RISCV_EXCP_LOAD_PAGE_FAULT,
                                                 (uint64_t)(&skip_instruction));
  uint64_t __attribute__((unused)) value_from_load_that_should_fault =
      load_from_address(PA);
  deregister_supervisor_mode_trap_handler_override(RISCV_EXCP_LOAD_PAGE_FAULT);

  if (PA_access_faulted == 0) {
    return DIAG_FAILED;
  }

  disable_mmu_from_supervisor_mode();

  // PA access should now succeed with the MMU off.
  uint64_t value_at_PA = load_from_address(PA);
  if (value_at_PA != new_magic_value) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
