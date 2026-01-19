/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdint.h>

#include "jumpstart.h"

__attr_mtext uint8_t get_physical_cpu_id_for_cpu_id_from_mmode(uint8_t cpu_id) {
  // Get the thread attributes struct address for the given cpu_id
  struct thread_attributes *thread_attributes_ptr =
      get_thread_attributes_for_cpu_id_from_mmode(cpu_id);

  return thread_attributes_ptr->physical_cpu_id;
}
