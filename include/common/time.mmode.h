/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <stdint.h>

/**
 * @brief Delays execution by the specified number of microseconds (M-mode)
 *
 * The function delays the execution of the program by (twiddling thumbs for)
 * the number of microseconds provided as a parameter.
 *
 * @param delay_in_useconds Number of microseconds to delay execution
 */
void delay_us_from_mmode(uint32_t delay_in_useconds);
