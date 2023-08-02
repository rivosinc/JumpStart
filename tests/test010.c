// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

extern uint64_t _machine_start;

int main(void) {
  uint64_t mmode_start_address = (uint64_t)&_machine_start;
  if (mmode_start_address != 0x80000000) {
    return DIAG_FAILED;
  }

  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0x80004000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_hart_id_from_supervisor_mode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_supervisor_mode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_diag_satp_mode_from_supervisor_mode() != SATP_MODE_SV39) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_supervisor_mode() !=
      SUPERVISOR_MODE_ENCODING) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
