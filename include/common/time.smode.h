/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <stdint.h>
#include <time.h>

/**
 * @brief Delays execution by the specified number of microseconds (S-mode)
 *
 * The function delays the execution of the program by (twiddling thumbs for)
 * the number of microseconds provided as a parameter.
 *
 * @param delay_in_useconds Number of microseconds to delay execution
 */
void delay_us_from_smode(uint32_t delay_in_useconds);

/**
 * @brief Get current time in seconds since epoch (S-mode)
 *
 * @param tloc Pointer to store the time, or NULL to just return the time
 * @return Current time in seconds since epoch, or (time_t)-1 on error
 */
time_t time(time_t *tloc);
