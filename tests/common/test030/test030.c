/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "heap.smode.h"
#include "jumpstart.h"
#include "tablewalk.smode.h"

extern uint64_t _JUMPSTART_CPU_SMODE_HEAP_START;
extern uint64_t _JUMPSTART_CPU_SMODE_HEAP_END;

extern int asm_test_unaligned_access(uint64_t, uint64_t);

int test_malloc(void);
int test_calloc(void);
int test_memalign(void);
int test_memcpy(void);
int test_memset(void);

#define MAGIC_VALUE8  0xca
#define MAGIC_VALUE16 0xcafe
#define MAGIC_VALUE32 0xcafecafe
#define MAGIC_VALUE64 0xcafecafecafecafe

#define ARRAY_LEN     10
int test_malloc(void) {
  uint8_t *x8 = malloc(sizeof(uint8_t));
  if (x8 == 0) {
    return DIAG_FAILED;
  }

  *x8 = MAGIC_VALUE8;
  if (*x8 != MAGIC_VALUE8) {
    return DIAG_FAILED;
  }

  uint16_t *x16 = malloc(sizeof(uint16_t));
  if (x16 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x16 & 0x1) != 0) {
    return DIAG_FAILED;
  }

  *x16 = MAGIC_VALUE16;
  if (*x16 != MAGIC_VALUE16) {
    return DIAG_FAILED;
  }

  uint32_t *x32 = malloc(sizeof(uint32_t));
  if (x32 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x32 & 0x3) != 0) {
    return DIAG_FAILED;
  }

  *x32 = MAGIC_VALUE32;
  if (*x32 != MAGIC_VALUE32) {
    return DIAG_FAILED;
  }

  uint64_t *x64 = malloc(sizeof(uint64_t));
  if (x64 == 0) {
    return DIAG_FAILED;
  }
  if (((uint64_t)x64 & 0x7) != 0) {
    return DIAG_FAILED;
  }

  *x64 = MAGIC_VALUE64;
  if (*x64 != MAGIC_VALUE64) {
    return DIAG_FAILED;
  }

  free(x8);
  free(x16);
  free(x32);
  free(x64);

  const uint64_t max_heap_size = (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_END -
                                 (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_START;

  void *y = malloc(max_heap_size / 2);
  if (y == 0) {
    return DIAG_FAILED;
  }

  void *z = malloc(max_heap_size / 2);
  if (z != 0) {
    return DIAG_FAILED;
  }

  free(y);

  z = malloc(max_heap_size / 2);
  if (z == 0) {
    return DIAG_FAILED;
  }

  x64 = malloc(max_heap_size / 2);
  if (x64 != 0) {
    return DIAG_FAILED;
  }

  free(z);

  return DIAG_PASSED;
}

int test_calloc(void) {
  uint8_t *z = calloc(ARRAY_LEN, sizeof(uint8_t));
  if (z == 0) {
    return DIAG_FAILED;
  }
  for (size_t i = 0; i < ARRAY_LEN; i++) {
    if (((uint8_t *)z)[i]) {
      return DIAG_FAILED;
    }
  }

  free(z);
  return DIAG_PASSED;
}

int test_memalign(void) {
  size_t alignments[] = {0x10, 0x100, 0x1000, 0x10000};
  for (unsigned i = 0; i < sizeof(alignments) / sizeof(size_t); i++) {
    uint8_t *z = memalign(alignments[i], sizeof(uint8_t));
    if (((uintptr_t)z) % alignments[i] != 0) {
      free(z);
      return DIAG_FAILED;
    }
    free(z);
  }
  return DIAG_PASSED;
}

int test_memcpy(void) {
  uint8_t *src = calloc(ARRAY_LEN, sizeof(uint8_t));
  uint8_t *dest = calloc(ARRAY_LEN, sizeof(uint8_t));

  if (!src || !dest) {
    return DIAG_FAILED;
  }

  for (size_t i = 0; i < ARRAY_LEN; i++) {
    src[i] = UINT8_C(MAGIC_VALUE8);
  }

  memcpy(dest, src, ARRAY_LEN);

  for (size_t i = 0; i < ARRAY_LEN; i++) {
    if (src[i] != dest[i]) {
      return DIAG_FAILED;
    }
  }
  free(src);
  free(dest);
  return DIAG_PASSED;
}

static void catch_memory_access_fault(void) {
  jumpstart_smode_fail();
}

int test_unaligned_access(void) {
  register_smode_trap_handler_override(RISCV_EXCP_LOAD_ACCESS_FAULT,
                                       (uint64_t)(&catch_memory_access_fault));
  register_smode_trap_handler_override(RISCV_EXCP_STORE_AMO_ACCESS_FAULT,
                                       (uint64_t)(&catch_memory_access_fault));

  const uint64_t max_heap_size = (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_END -
                                 (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_START;
  // Allocate 2MB of memory.
  uint64_t allocation_size = 2 * 1024 * 1024;
  if (max_heap_size < allocation_size) {
    return DIAG_FAILED;
  }

  // FIXME: The current malloc implementation will fail if we allocate
  // 2MB in one go.
  uint64_t *buffer_1 = memalign(16, allocation_size / 2);
  if (!buffer_1) {
    return DIAG_FAILED;
  }
  uint64_t *buffer_2 = memalign(16, allocation_size / 2);
  if (!buffer_2) {
    return DIAG_FAILED;
  }

  int result =
      asm_test_unaligned_access((uint64_t)buffer_1, allocation_size / 2);

  result |= asm_test_unaligned_access((uint64_t)buffer_2, allocation_size / 2);

  free(buffer_1);
  free(buffer_2);
  return result;
}

int test_memset(void) {
  uint8_t *src = calloc(ARRAY_LEN, sizeof(uint8_t));

  if (!src) {
    return DIAG_FAILED;
  }

  memset(src, MAGIC_VALUE8, ARRAY_LEN);

  for (size_t i = 0; i < ARRAY_LEN; i++) {
    if (src[i] != UINT8_C(MAGIC_VALUE8)) {
      return DIAG_FAILED;
    }
  }
  free(src);
  return DIAG_PASSED;
}

int main(void) {
  if (test_malloc() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_calloc() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_memalign() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_memcpy() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_memset() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  if (test_unaligned_access() != DIAG_PASSED) {
    return DIAG_FAILED;
  }
  return DIAG_PASSED;
}
