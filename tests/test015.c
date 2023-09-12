// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "imsic_functions.supervisor.h"
#include "jumpstart_functions.h"

volatile uint64_t irq_var = 0;
volatile uint8_t hart_imsic_enabled[MAX_NUM_HARTS_SUPPORTED] = {0};

static void test008_exception_handler(void) {
  irq_var = 1;
  write_csr(stopei, 0);
}

int main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();

  if (hart_id == PRIMARY_HART_ID) {
    uint64_t active_hart_mask = get_active_hart_mask_from_supervisor_mode();

    uint8_t current_hart_id = 0;
    while (active_hart_mask != 0) {
      if (current_hart_id != hart_id && (active_hart_mask & 0x1)) {
        while (hart_imsic_enabled[current_hart_id] == 0)
          ;

        send_ipi_to_supervisor_mode(current_hart_id);
      }

      active_hart_mask >>= 1;
      ++current_hart_id;
    }
  } else {
    register_supervisor_mode_trap_handler_override(
        SCAUSE_INT_EXTERNAL | (1ULL << SCAUSE_INTERRUPT_BIT_LSB),
        (uint64_t)(&test008_exception_handler));

    imsic_init();

    imsic_id_enable(IMSIC_IPI_ID);

    hart_imsic_enabled[hart_id] = 1;
    asm volatile("wfi");

    if (irq_var != 1) {
      return DIAG_FAILED;
    }

    imsic_id_disable(IMSIC_IPI_ID);
    imsic_fini();
  }

  return DIAG_PASSED;
}
