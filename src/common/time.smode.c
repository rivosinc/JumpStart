// SPDX-FileCopyrightText: 2024 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <stdint.h>
#include <sys/time.h>
#include <time.h>

#include "jumpstart.h"

__attr_stext static inline uint64_t read_time() {
  uint64_t time_val;
  asm volatile("rdtime %0" : "=r"(time_val));
  return time_val;
}

__attr_stext int gettimeofday(struct timeval *tv,
                              void *tz __attribute__((unused))) {
  uint64_t timer_ticks = read_time();

  // Convert timer ticks to seconds and microseconds
  uint64_t seconds = timer_ticks / (CPU_CLOCK_FREQUENCY_IN_MHZ * 1000000);
  uint64_t microseconds =
      (timer_ticks % (CPU_CLOCK_FREQUENCY_IN_MHZ * 1000000));

  tv->tv_sec = seconds;
  tv->tv_usec = microseconds;

  return 0; // Success
}

__attr_stext time_t time(time_t *tloc) {
  struct timeval tv;

  // Call gettimeofday() to get the current time
  if (gettimeofday(&tv, NULL) != 0) {
    return (time_t)-1; // Error case
  }

  // Extract the seconds part
  time_t current_time = (time_t)tv.tv_sec;

  // If tloc is not NULL, store the time in the location pointed to by tloc
  if (tloc != NULL) {
    *tloc = current_time;
  }

  return current_time; // Return the current time in seconds
}
