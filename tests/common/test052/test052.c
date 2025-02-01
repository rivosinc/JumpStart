/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

int assert(int condition) {
  return condition ? DIAG_PASSED : DIAG_FAILED;
}

// Unit tests for strlen
int test_strlen() {
  static const char str1[] = "hello";
  static const char str2[] = "";
  static const char str3[] = "baremetal";
  static const char str4[] = "hello SeNtiNel";

  if (assert(strlen(str1) == sizeof(str1) - 1) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strlen(str2) == sizeof(str2) - 1) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strlen(str3) == sizeof(str3) - 1) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strlen(str4) == sizeof(str4) - 1) != DIAG_PASSED)
    return DIAG_FAILED;

  return DIAG_PASSED;
}

// Unit tests for strcpy
int test_strcpy() {
  char dest[20];

  strcpy(dest, "hello");
  if (assert(strcmp(dest, "hello") == 0) != DIAG_PASSED)
    return DIAG_FAILED;

  strcpy(dest, "baremetal");
  if (assert(strcmp(dest, "baremetal") == 0) != DIAG_PASSED)
    return DIAG_FAILED;

  strcpy(dest, "");
  if (assert(strcmp(dest, "") == 0) != DIAG_PASSED)
    return DIAG_FAILED;

  return DIAG_PASSED;
}

// Unit tests for strcmp
int test_strcmp() {
  if (assert(strcmp("hello", "hello") == 0) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strcmp("hello", "world") != 0) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strcmp("abc", "abcd") < 0) != DIAG_PASSED)
    return DIAG_FAILED;
  if (assert(strcmp("abcd", "abc") > 0) != DIAG_PASSED)
    return DIAG_FAILED;

  return DIAG_PASSED; // Success
}

int main() {
  // Run tests and check for DIAG_FAILED
  if (test_strlen() != DIAG_PASSED)
    return DIAG_FAILED;
  if (test_strcpy() != DIAG_PASSED)
    return DIAG_FAILED;
  if (test_strcmp() != DIAG_PASSED)
    return DIAG_FAILED;

  // If no failures, return DIAG_PASSED
  return DIAG_PASSED;
}
