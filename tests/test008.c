// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"
#include "jumpstart_imsic.h"

volatile uint64_t irq_var = 0;

static void test008_exception_handler(void) {
  irq_var = 1;
  write_csr(stopei, 0);
}

int main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id();

  register_trap_handler_override(SUPERVISOR_MODE_ENCODING,
                                 SCAUSE_INT_EXTERNAL |
                                     (1ULL << SCAUSE_INTERRUPT_BIT_LSB),
                                 (uint64_t)(&test008_exception_handler));

  setup_mmu_for_supervisor_mode();
  imsic_init();
  imsic_id_enable(IMSIC_IPI_ID);

  send_ipi_to_supervisor_mode(hart_id);

  asm volatile("wfi");

  if (irq_var != 1)
    return 1;

  disable_mmu_for_supervisor_mode();
  imsic_id_disable(IMSIC_IPI_ID);
  imsic_fini();
  return 0;
}