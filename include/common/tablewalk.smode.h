/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <inttypes.h>

#define MAX_NUM_PAGE_TABLE_LEVELS 4

struct translation_info {
  uint8_t satp_mode;
  uint8_t levels_traversed;
  uint8_t walk_successful;
  uint64_t va;
  uint64_t pa;
  uint64_t pte_address[MAX_NUM_PAGE_TABLE_LEVELS];
  uint64_t pte_value[MAX_NUM_PAGE_TABLE_LEVELS];
};

void translate_VA(uint64_t va, struct translation_info *xlate_info);
