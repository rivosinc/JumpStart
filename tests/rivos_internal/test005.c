// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

extern uint64_t source_area;
extern uint64_t dest_area;
extern uint64_t source_area_end;
extern uint64_t dest_area_end;

int main(void) {
  uint64_t *source_area_ptr = (uint64_t *)&source_area;
  uint64_t *source_area_end_ptr = (uint64_t *)&source_area_end;
  uint64_t *dest_area_ptr = (uint64_t *)&dest_area;
  uint64_t *dest_area_end_ptr = (uint64_t *)&dest_area_end;

  uint64_t source_area_size =
      (uint64_t)source_area_end_ptr - (uint64_t)source_area_ptr;
  uint64_t dest_area_size =
      (uint64_t)dest_area_end_ptr - (uint64_t)dest_area_ptr;

  if (source_area_size != dest_area_size) {
    return DIAG_FAILED;
  }

  for (uint32_t i = 0; (&source_area_ptr[i]) < source_area_end_ptr; ++i) {
    dest_area_ptr[i] = source_area_ptr[i];
  }

  for (uint32_t i = 0; (&source_area_ptr[i]) < source_area_end_ptr; ++i) {
    if (dest_area_ptr[i] != source_area_ptr[i]) {
      return DIAG_FAILED;
    }
  }

  return DIAG_PASSED;
}