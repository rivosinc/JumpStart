/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

#include "uart.smode.h"

extern uint64_t _TEXT_START;
extern uint64_t _DATA_4K_START;
extern uint64_t _DATA_4K_2_START;
extern uint64_t _DATA_2MB_START;
extern uint64_t _DATA_2MB_WITH_EXPLICIT_ADDRESS_START;

__attribute__((section(".data_4K"))) uint64_t data_var = 0x12345678;
__attribute__((section(".data_4K_2"))) uint64_t data_var_2 = 0x12345678;

__attribute__((section(".data_2MB"))) uint64_t data_2mb_var = 0x12345678;
__attribute__((section(".data_2MB_with_explicit_address"))) uint64_t
    data_2mb_with_explicit_address_var = 0x12345678;

int main(void) {
  uint64_t main_function_address = (uint64_t)&main;
  volatile uint64_t text_section_start = (uint64_t)(&_TEXT_START);
  if (main_function_address != text_section_start) {
    return DIAG_FAILED;
  }

  // Check that the data_var is in the data section.
  volatile uint64_t data_section_start = (uint64_t)(&_DATA_4K_START);
  if ((uint64_t)&data_var != data_section_start) {
    return DIAG_FAILED;
  }

  volatile uint64_t data_4k_2_section_start = (uint64_t)(&_DATA_4K_2_START);
  if ((uint64_t)&data_var_2 != data_4k_2_section_start) {
    return DIAG_FAILED;
  }

  volatile uint64_t data_2mb_section_start = (uint64_t)(&_DATA_2MB_START);
  if ((uint64_t)&data_2mb_var != data_2mb_section_start) {
    return DIAG_FAILED;
  }

  volatile uint64_t data_2mb_with_explicit_address_section_start =
      (uint64_t)(&_DATA_2MB_WITH_EXPLICIT_ADDRESS_START);
  if ((uint64_t)&data_2mb_with_explicit_address_var !=
      data_2mb_with_explicit_address_section_start) {
    return DIAG_FAILED;
  }

  // We expect jumpstart to sort the mappings by page_size first, then by
  // mappings that don't have addresses.
  if (data_4k_2_section_start >= data_2mb_section_start) {
    return DIAG_FAILED;
  }
  if (data_2mb_section_start >= data_2mb_with_explicit_address_section_start) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
