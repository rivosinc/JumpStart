// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

/*
Restoring translation-data coherence:
  TEST: CoRpteTf.inv+sfence.vma

Initial condition:
PTE(X) = (OA=PA_X, V=0)

Hart0’s instructions:
(H0.0)	Store (OA=PA_X) to PTE(X)

Hart1’s instructions:
(H1.0) Load from PTE(X)
(H1.1) Execute an SFENCE.VMA
(H1.2) Load from X

Question:
  Can H1.0 return (OA=PA_X) and H1.2 fault?
Ved: Answer - No
*/

#include "jumpstart_functions.h"
#include "tablewalk_functions.supervisor.h"

uint8_t is_load_allowed_to_data_area(void);

extern uint64_t data_area;
uint64_t data_area_address = (uint64_t)&data_area;

void hart1_load_page_fault_handler(void);
void hart1_load_page_fault_handler(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();
  if (hart_id != 1) {
    jumpstart_supervisor_fail();
  }

  uint64_t stval_value = read_csr(stval);
  if (stval_value != data_area_address) {
    jumpstart_supervisor_fail();
  }

  // skip over the faulting load
  uint64_t sepc_value = read_csr(sepc);
  sepc_value += 4;
  write_csr(sepc, sepc_value);
}

int main(void) {
  uint8_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();
  if (hart_id > 1) {
    return DIAG_FAILED;
  }

  struct translation_info xlate_info;
  translate_VA(data_area_address, &xlate_info);

  // The translation should exist but should be marked with V=0 at this
  // point in the memory map.
  if (xlate_info.walk_successful != 0 || xlate_info.levels_traversed != 3 ||
      (xlate_info.pte_value[2] & PTE_VALID_BIT_MASK) != 0) {
    return DIAG_FAILED;
  }

  if (hart_id == 1) {
    register_supervisor_mode_trap_handler_override(
        SCAUSE_EC_LOAD_PAGE_FAULT, (uint64_t)(&hart1_load_page_fault_handler));

    if (is_load_allowed_to_data_area() == 1) {
      return DIAG_FAILED;
    }
  }

  sync_all_harts_from_supervisor_mode();

  if (hart_id == 0) {
    *((uint64_t *)xlate_info.pte_address[2]) =
        xlate_info.pte_value[2] | PTE_VALID_BIT_MASK;
    asm volatile("sfence.vma");
  } else {
    while (1) {
      translate_VA(data_area_address, &xlate_info);

      if (xlate_info.walk_successful == 1) {
        // The new PTE is now valid, so the load should succeed.
        if (is_load_allowed_to_data_area() == 0) {
          return DIAG_FAILED;
        }
        break;
      }
    }
  }

  return DIAG_PASSED;
}
