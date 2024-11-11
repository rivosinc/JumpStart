// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"
#include "uart.smode.h"

#include <sys/time.h>
#include <time.h>

// Function to check if time() is working correctly
int test_time() {
  time_t current_time = time(NULL);
  if (current_time == (time_t)-1) {
    printk("test_time: FAILED - time() returned -1\n");
    return DIAG_FAILED;
  } else {
    printk("test_time: PASSED - current time: %ld\n", current_time);
    return DIAG_PASSED;
  }
}

// Function to check if gettimeofday() is working correctly
int test_gettimeofday() {
  struct timeval tv;
  int result = gettimeofday(&tv, NULL);

  printk("test_gettimeofday: define CPU_CLOCK_FREQUENCY_IN_MHZ %d\n",
         CPU_CLOCK_FREQUENCY_IN_MHZ);

  if (result != 0) {
    printk("test_gettimeofday: FAILED - gettimeofday() returned %d\n", result);
    return DIAG_FAILED;
  } else if (tv.tv_sec < 0 || tv.tv_usec < 0 || tv.tv_usec >= 1000000) {
    printk("test_gettimeofday: FAILED - invalid time values: %ld seconds, %ld "
           "microseconds\n",
           tv.tv_sec, tv.tv_usec);
    return DIAG_FAILED;
  } else {
    printk("test_gettimeofday: PASSED - time: %ld seconds, %ld microseconds\n",
           tv.tv_sec, tv.tv_usec);
    return DIAG_PASSED;
  }
}

// Main function to run the tests
int main() {
  if (test_time() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_gettimeofday() != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  return DIAG_PASSED;
}
