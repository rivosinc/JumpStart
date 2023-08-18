// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

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
  if (get_thread_attributes_hart_id_from_supervisor_mode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_supervisor_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_supervisor_mode() !=
      SUPERVISOR_MODE_ENCODING) {
    return DIAG_FAILED;
  }

  register_supervisor_mode_trap_handler_override(
      SCAUSE_EC_ILLEGAL_INSTRUCTION, (uint64_t)(&test011_exception_handler));

  if (run_function_in_user_mode((uint64_t)test_illegal_instruction_in_umode) !=
      0) {
    return DIAG_FAILED;
  }

  if (excep_rcvd != 0xabcdabcd) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
