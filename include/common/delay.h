/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <stdint.h>

/**
 * @brief Macro for delay_us implementation that works in both mmode and smode
 *
 * This macro provides the core delay_us functionality that can be used by
 * both mmode and smode implementations. It takes a parameter for the delay
 * in microseconds and implements the delay using cycle counting and pause
 * instructions.
 *
 * @param __delay_in_useconds Number of microseconds to delay execution
 */
#define _delay_us(__delay_in_useconds)                                         \
  ({                                                                           \
    register volatile uint64_t __start_time, __end_time;                       \
    const uint32_t __iter_count = 10;                                          \
    __start_time = read_csr(CSR_TIME);                                         \
    for (uint32_t __i = 0; __i < __iter_count; __i++) {                        \
      asm volatile("pause");                                                   \
    }                                                                          \
    __end_time = read_csr(CSR_TIME);                                           \
    uint64_t __avg_lat = (__end_time - __start_time) / __iter_count;           \
    /* Check if delay has already completed within iter_count */               \
    if ((__delay_in_useconds / __avg_lat) <= __iter_count) {                   \
      /* Delay already completed, no additional iterations needed */           \
    } else {                                                                   \
      uint32_t __latency_iter_count =                                          \
          (__delay_in_useconds / __avg_lat) - __iter_count;                    \
      for (uint32_t __i = 0; __i < __latency_iter_count; __i++) {              \
        asm volatile("pause");                                                 \
      }                                                                        \
    }                                                                          \
  })
