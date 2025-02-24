/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdbool.h>

#include "cpu_bits.h"
#include "hbm.h"
#include "heap.smode.h"
#include "jumpstart.h"
#include "tablewalk.smode.h"
#include "uart.smode.h"

extern uint64_t _JUMPSTART_CPU_SMODE_HEAP_START;
extern uint64_t _JUMPSTART_CPU_SMODE_HEAP_END;

extern int asm_test_unaligned_access(uint64_t, uint64_t);

#define MAGIC_VALUE8  0xca
#define MAGIC_VALUE16 0xcafe
#define MAGIC_VALUE32 0xcafecafe
#define MAGIC_VALUE64 0xcafecafecafecafe

#define ARRAY_LEN     10

int test_malloc(uint8_t backing_memory, uint8_t memory_type) {
  uint8_t *x8 =
      malloc_from_memory(sizeof(uint8_t), backing_memory, memory_type);
  if (x8 == 0) {
    return DIAG_FAILED;
  }

  *x8 = MAGIC_VALUE8;
  if (*x8 != MAGIC_VALUE8) {
    return DIAG_FAILED;
  }

  uint16_t *x16 =
      malloc_from_memory(sizeof(uint16_t), backing_memory, memory_type);
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

  uint32_t *x32 =
      malloc_from_memory(sizeof(uint32_t), backing_memory, memory_type);
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

  uint64_t *x64 =
      malloc_from_memory(sizeof(uint64_t), backing_memory, memory_type);
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

  free_from_memory(x8, backing_memory, memory_type);
  free_from_memory(x16, backing_memory, memory_type);
  free_from_memory(x32, backing_memory, memory_type);
  free_from_memory(x64, backing_memory, memory_type);

  const uint64_t max_heap_size = get_heap_size(backing_memory, memory_type);

  void *y = malloc_from_memory(max_heap_size / 2, backing_memory, memory_type);
  if (y == 0) {
    return DIAG_FAILED;
  }

  void *z = malloc_from_memory(max_heap_size / 2, backing_memory, memory_type);
  if (z != 0) {
    return DIAG_FAILED;
  }

  free_from_memory(y, backing_memory, memory_type);

  z = malloc_from_memory(max_heap_size / 2, backing_memory, memory_type);
  if (z == 0) {
    return DIAG_FAILED;
  }

  x64 = malloc_from_memory(max_heap_size / 2, backing_memory, memory_type);
  if (x64 != 0) {
    return DIAG_FAILED;
  }

  free_from_memory(z, backing_memory, memory_type);

  return DIAG_PASSED;
}

int test_calloc(uint8_t backing_memory, uint8_t memory_type) {
  uint8_t *z = calloc_from_memory(ARRAY_LEN, sizeof(uint8_t), backing_memory,
                                  memory_type);
  if (z == 0) {
    return DIAG_FAILED;
  }
  for (size_t i = 0; i < ARRAY_LEN; i++) {
    if (((uint8_t *)z)[i]) {
      return DIAG_FAILED;
    }
  }

  free_from_memory(z, backing_memory, memory_type);
  return DIAG_PASSED;
}

int test_memalign(uint8_t backing_memory, uint8_t memory_type) {
  size_t alignments[] = {0x10, 0x100, 0x1000, 0x10000};
  for (unsigned i = 0; i < sizeof(alignments) / sizeof(size_t); i++) {
    uint8_t *z = memalign_from_memory(alignments[i], sizeof(uint8_t),
                                      backing_memory, memory_type);
    if (((uintptr_t)z) % alignments[i] != 0) {
      free_from_memory(z, backing_memory, memory_type);
      return DIAG_FAILED;
    }
    free_from_memory(z, backing_memory, memory_type);
  }
  return DIAG_PASSED;
}

#ifdef __clang__
__attribute__((optnone))
#endif
int test_memcpy(uint8_t backing_memory, uint8_t memory_type) {
  uint8_t *src = calloc_from_memory(ARRAY_LEN, sizeof(uint8_t), backing_memory,
                                    memory_type);
  uint8_t *dest = calloc_from_memory(ARRAY_LEN, sizeof(uint8_t), backing_memory,
                                     memory_type);

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
  free_from_memory(src, backing_memory, memory_type);
  free_from_memory(dest, backing_memory, memory_type);
  return DIAG_PASSED;
}

static void catch_memory_access_fault(void) {
  jumpstart_smode_fail();
}

int test_unaligned_access(uint8_t backing_memory, uint8_t memory_type) {
  register_smode_trap_handler_override(RISCV_EXCP_LOAD_ACCESS_FAULT,
                                       (uint64_t)(&catch_memory_access_fault));
  register_smode_trap_handler_override(RISCV_EXCP_STORE_AMO_ACCESS_FAULT,
                                       (uint64_t)(&catch_memory_access_fault));

  const uint64_t max_heap_size = get_heap_size(backing_memory, memory_type);

  // Use 1/4 of heap size for each buffer, ensuring we don't exceed heap
  // capacity
  uint64_t allocation_size = max_heap_size / 4;
  if (allocation_size < 4096) { // Ensure minimum reasonable size for testing
    return DIAG_FAILED;
  }

  uint64_t *buffer_1 =
      memalign_from_memory(16, allocation_size, backing_memory, memory_type);
  if (!buffer_1) {
    return DIAG_FAILED;
  }
  uint64_t *buffer_2 =
      memalign_from_memory(16, allocation_size, backing_memory, memory_type);
  if (!buffer_2) {
    return DIAG_FAILED;
  }

  int result = asm_test_unaligned_access((uint64_t)buffer_1, allocation_size);

  result |= asm_test_unaligned_access((uint64_t)buffer_2, allocation_size);

  free_from_memory(buffer_1, backing_memory, memory_type);
  free_from_memory(buffer_2, backing_memory, memory_type);
  return result;
}

int test_memset(uint8_t backing_memory, uint8_t memory_type) {
  uint8_t *src = calloc_from_memory(ARRAY_LEN, sizeof(uint8_t), backing_memory,
                                    memory_type);

  if (!src) {
    return DIAG_FAILED;
  }

  memset(src, MAGIC_VALUE8, ARRAY_LEN);

  for (size_t i = 0; i < ARRAY_LEN; i++) {
    if (src[i] != UINT8_C(MAGIC_VALUE8)) {
      return DIAG_FAILED;
    }
  }
  free_from_memory(src, backing_memory, memory_type);
  return DIAG_PASSED;
}

int test_heap_type(uint8_t backing_memory, uint8_t memory_type,
                   uint64_t expected_start, uint64_t expected_end,
                   bool test_unaligned) {
  printk("Testing heap type - backing_memory: %d, memory_type: %d\n",
         backing_memory, memory_type);
  printk("Expected range: 0x%lx - 0x%lx\n", expected_start, expected_end);

  // Verify heap allocation works within expected range
  uint64_t mem_address =
      (uint64_t)malloc_from_memory(1024, backing_memory, memory_type);
  printk("Allocated address: 0x%lx\n", mem_address);

  if (mem_address < expected_start || mem_address >= expected_end) {
    printk("ERROR: Address 0x%lx outside expected range!\n", mem_address);
    return DIAG_FAILED;
  }
  free_from_memory((void *)mem_address, backing_memory, memory_type);

  // Run standard memory tests
  printk("Running memory tests...\n");
  if (test_malloc(backing_memory, memory_type) != DIAG_PASSED ||
      test_calloc(backing_memory, memory_type) != DIAG_PASSED ||
      test_memalign(backing_memory, memory_type) != DIAG_PASSED ||
      test_memcpy(backing_memory, memory_type) != DIAG_PASSED ||
      test_memset(backing_memory, memory_type) != DIAG_PASSED) {
    printk("ERROR: Standard memory tests failed!\n");
    return DIAG_FAILED;
  }

  // Only test unaligned access for WB memory
  if (test_unaligned) {
    printk("Running unaligned access test...\n");
    if (test_unaligned_access(backing_memory, memory_type) != DIAG_PASSED) {
      printk("ERROR: Unaligned access test failed!\n");
      return DIAG_FAILED;
    }
  }

  printk("All tests passed for this heap type\n");
  return DIAG_PASSED;
}

int main(void) {
  printk("\n=== Starting heap tests ===\n");

  uint64_t expected_heap_start = (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_START;
  uint64_t expected_heap_end = (uint64_t)&_JUMPSTART_CPU_SMODE_HEAP_END;

  // Test DDR WB heap (default heap)
  if (test_heap_type(BACKING_MEMORY_DDR, MEMORY_TYPE_WB, expected_heap_start,
                     expected_heap_end, true) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // Test DDR UC heap
  setup_heap(0xA0200000, 0xA0200000 + 4 * 1024 * 1024, BACKING_MEMORY_DDR,
             MEMORY_TYPE_UC);
  if (test_heap_type(BACKING_MEMORY_DDR, MEMORY_TYPE_UC, 0xA0200000,
                     0xA0200000 + 4 * 1024 * 1024, false) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // Test DDR WC heap
  setup_heap(0xA0600000, 0xA0600000 + 4 * 1024 * 1024, BACKING_MEMORY_DDR,
             MEMORY_TYPE_WC);
  if (test_heap_type(BACKING_MEMORY_DDR, MEMORY_TYPE_WC, 0xA0600000,
                     0xA0600000 + 4 * 1024 * 1024, false) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

#if ENABLE_HBM_TESTS == 1
  // Test HBM WB heap
  setup_heap(0x2000000000, 0x2000000000 + 2 * 1024 * 1024, BACKING_MEMORY_HBM,
             MEMORY_TYPE_WB);
  if (test_heap_type(BACKING_MEMORY_HBM, MEMORY_TYPE_WB, 0x2000000000,
                     0x2000000000 + 2 * 1024 * 1024, true) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // Test HBM UC heap
  setup_heap(0x2000200000, 0x2000200000 + 2 * 1024 * 1024, BACKING_MEMORY_HBM,
             MEMORY_TYPE_UC);
  if (test_heap_type(BACKING_MEMORY_HBM, MEMORY_TYPE_UC, 0x2000200000,
                     0x2000200000 + 2 * 1024 * 1024, false) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  // Test HBM WC heap
  setup_heap(0x2000400000, 0x2000400000 + 2 * 1024 * 1024, BACKING_MEMORY_HBM,
             MEMORY_TYPE_WC);
  if (test_heap_type(BACKING_MEMORY_HBM, MEMORY_TYPE_WC, 0x2000400000,
                     0x2000400000 + 2 * 1024 * 1024, false) != DIAG_PASSED) {
    return DIAG_FAILED;
  }

  deregister_heap(BACKING_MEMORY_HBM, MEMORY_TYPE_WB);
  deregister_heap(BACKING_MEMORY_HBM, MEMORY_TYPE_UC);
  deregister_heap(BACKING_MEMORY_HBM, MEMORY_TYPE_WC);
#endif /* ENABLE_HBM_TESTS == 1 */

  deregister_heap(BACKING_MEMORY_DDR, MEMORY_TYPE_UC);
  deregister_heap(BACKING_MEMORY_DDR, MEMORY_TYPE_WC);

  return DIAG_PASSED;
}
