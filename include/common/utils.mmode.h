/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <inttypes.h>

int32_t mmode_try_get_seed(void);
int32_t get_random_number_from_mmode(void);
void set_random_seed_from_mmode(int32_t seed);
