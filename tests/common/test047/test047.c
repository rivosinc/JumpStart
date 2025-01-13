// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart.h"

struct {
  uint8_t b;
  uint16_t h;
  uint32_t w;
  uint64_t d;
} vsdata __attribute__((section(".data.vsmode")));

uint64_t smode_read_guest_byte(uintptr_t);
uint64_t smode_read_guest_byte_zext(uintptr_t);
uint64_t smode_read_guest_hword(uintptr_t);
uint64_t smode_read_guest_hword_zext(uintptr_t);
uint64_t smode_read_guest_word(uintptr_t);
uint64_t smode_read_guest_word_zext(uintptr_t);
uint64_t smode_read_guest_dword(uintptr_t);
void smode_write_guest_byte(uintptr_t, uint8_t);
void smode_write_guest_hword(uintptr_t, uint16_t);
void smode_write_guest_word(uintptr_t, uint32_t);
void smode_write_guest_dword(uintptr_t, uint64_t);
uint8_t smode_read_guest_inst_byte(uintptr_t);
uint16_t smode_read_guest_inst_hword(uintptr_t);

void vsmode_set_data(uint8_t b, uint16_t h, uint32_t w, uint64_t d)
    __attribute__((section(".text.vsmode")));
int vsmode_check_data(uint8_t b, uint16_t h, uint32_t w, uint64_t d)
    __attribute__((section(".text.vsmode")));

void vsmode_set_data(uint8_t b, uint16_t h, uint32_t w, uint64_t d) {
  vsdata.b = b;
  vsdata.h = h;
  vsdata.w = w;
  vsdata.d = d;
}

int vsmode_check_data(uint8_t b, uint16_t h, uint32_t w, uint64_t d) {
  if (vsdata.b != b)
    return DIAG_FAILED;

  if (vsdata.h != h)
    return DIAG_FAILED;

  if (vsdata.w != w)
    return DIAG_FAILED;

  if (vsdata.d != d)
    return DIAG_FAILED;

  return DIAG_PASSED;
}

int main(void) {

  // Set data in vsmode.
  run_function_in_vsmode((uint64_t)vsmode_set_data, 0x80, 0x8000, 0x80000000,
                         0x8000000000000000);

  // Read data from hsmode.
  if (smode_read_guest_byte((uintptr_t)&vsdata.b) != 0xffffffffffffff80) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_byte_zext((uintptr_t)&vsdata.b) != 0x80) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_hword((uintptr_t)&vsdata.h) != 0xffffffffffff8000) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_hword_zext((uintptr_t)&vsdata.h) != 0x8000) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_word((uintptr_t)&vsdata.w) != 0xffffffff80000000) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_word_zext((uintptr_t)&vsdata.w) != 0x80000000) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_dword((uintptr_t)&vsdata.d) != 0x8000000000000000) {
    return DIAG_FAILED;
  }

  // Set data from hsmode.
  smode_write_guest_byte((uintptr_t)&vsdata.b, 0x7f);
  smode_write_guest_hword((uintptr_t)&vsdata.h, 0x7fff);
  smode_write_guest_word((uintptr_t)&vsdata.w, 0x7fffffff);
  smode_write_guest_dword((uintptr_t)&vsdata.d, 0x7fffffffffffffff);

  // Check data in vsmode.
  if (run_function_in_vsmode((uint64_t)vsmode_check_data, 0x7f, 0x7fff,
                             0x7fffffff, 0x7fffffffffffffff) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // One last check in hsmode.
  if (smode_read_guest_byte((uintptr_t)&vsdata.b) != 0x7f) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_byte_zext((uintptr_t)&vsdata.b) != 0x7f) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_hword((uintptr_t)&vsdata.h) != 0x7fff) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_hword_zext((uintptr_t)&vsdata.h) != 0x7fff) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_word((uintptr_t)&vsdata.w) != 0x7fffffff) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_word_zext((uintptr_t)&vsdata.w) != 0x7fffffff) {
    return DIAG_FAILED;
  }
  if (smode_read_guest_dword((uintptr_t)&vsdata.d) != 0x7fffffffffffffff) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
