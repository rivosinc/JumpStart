// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

extern uint64_t _JUMPSTART_TEXT_MMODE_INIT_START;
extern uint64_t _JUMPSTART_TEXT_SMODE_START;
extern uint64_t _JUMPSTART_TEXT_UMODE_START;

int main(void) {
  uint64_t mmode_start_address = (uint64_t)&_JUMPSTART_TEXT_MMODE_INIT_START;
  if (mmode_start_address != 0x81000000) {
    return DIAG_FAILED;
  }

  uint64_t smode_start_address = (uint64_t)&_JUMPSTART_TEXT_SMODE_START;
  if (smode_start_address != 0x82000000) {
    return DIAG_FAILED;
  }

  uint64_t umode_start_address = (uint64_t)&_JUMPSTART_TEXT_UMODE_START;
  if (umode_start_address != 0x83000000) {
    return DIAG_FAILED;
  }

  uint64_t main_function_address = (uint64_t)&main;
  if (main_function_address != 0xC0020000) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_hart_id_from_smode() != 0) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_bookend_magic_number_from_smode() !=
      THREAD_ATTRIBUTES_BOOKEND_MAGIC_NUMBER_VALUE) {
    return DIAG_FAILED;
  }

  if (get_diag_satp_mode_from_smode() != VM_1_10_SV39) {
    return DIAG_FAILED;
  }

  if (get_thread_attributes_current_mode_from_smode() != PRV_S) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
