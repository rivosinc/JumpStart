// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

int test_illegal_instruction_in_umode(void);

static volatile uint32_t excep_rcvd = 0;

static void test011_exception_handler(void) {
  uint64_t reg = read_csr(sepc);

  /* Just skip the illegal instruction and move to next instruction. */
  write_csr(sepc, reg + 4);

  /* Set excep_rcvd to non-zero to notify main that exception occurred. */
  excep_rcvd = 0xabcdabcd;
}

int main(void) {
  if (get_thread_attributes_hart_id_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  register_smode_trap_handler_override(RISCV_EXCP_ILLEGAL_INST,
                                       (uint64_t)(&test011_exception_handler));

  if (run_function_in_umode((uint64_t)test_illegal_instruction_in_umode) != 0) {
    return DIAG_FAILED;
  }

  if (excep_rcvd != 0xabcdabcd) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
