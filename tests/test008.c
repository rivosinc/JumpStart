// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "imsic_functions.supervisor.h"
#include "jumpstart_functions.h"

volatile uint64_t irq_var = 0;

static void test008_exception_handler(void) {
  irq_var = 1;
  write_csr(stopei, 0);
}

int main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_supervisor_mode();

  register_supervisor_mode_trap_handler_override(
      SCAUSE_INT_EXTERNAL | (1ULL << SCAUSE_INTERRUPT_BIT_LSB),
      (uint64_t)(&test008_exception_handler));

  imsic_init();
  imsic_id_enable(IMSIC_IPI_ID);

  send_ipi_to_supervisor_mode(hart_id);

  asm volatile("wfi");

  if (irq_var != 1)
    return DIAG_FAILED;

  imsic_id_disable(IMSIC_IPI_ID);
  imsic_fini();
  return DIAG_PASSED;
}
