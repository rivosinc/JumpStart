// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "heap.smode.h"
#include "jumpstart.h"
/*
Multithreaded Malloc Test:

In this test, we perform "ALLOCS_PER_HART" memory allocations for
"NUM_ITERATION" iterations. we store the pointer of all memory allocation for
every hart/iteration in a allocation table.
We expect all the pointers across harts for a given iteration to be unique.
*/

#define NUM_INTERATIONS 10
#define ALLOCS_PER_HART 16

void *allocated[MAX_NUM_HARTS_SUPPORTED][NUM_INTERATIONS][ALLOCS_PER_HART] = {
    0};

static uint64_t allocation_entropy(uint64_t seed_hash, uint64_t hart_id,
                                   uint64_t iter, uint64_t alloc_index) {
  uint64_t hash = seed_hash;
  const uint64_t magic = 0x9e3779b9;
  hash ^= hart_id + magic + (hash << 6) + (hash >> 2);
  hash ^= iter + magic + (hash << 6) + (hash >> 2);
  hash ^= alloc_index + magic + (hash << 6) + (hash >> 2);
  return hash;
}

static uint64_t get_allocation_size(uint64_t hart_id, uint64_t iter,
                                    uint64_t alloc_index) {
  const uint64_t alloc_sizes[] = {8, 16, 32, 48, 64};
  uint64_t hash = allocation_entropy(0, hart_id, iter, alloc_index);
  return alloc_sizes[hash % (sizeof(alloc_sizes) / sizeof(uint64_t))];
}

static uint64_t get_allocation_align(uint64_t hart_id, uint64_t iter,
                                     uint64_t alloc_index) {
  const uint64_t aligns[] = {0x8, 0x10, 0x100};
  uint64_t hash = allocation_entropy(0, hart_id, iter, alloc_index);
  hash = allocation_entropy(hash, hart_id, iter, alloc_index);
  return aligns[hash % (sizeof(aligns) / sizeof(uint64_t))];
}

static int make_allocations(uint64_t hart_id, int iter) {
  for (int j = 0; j < ALLOCS_PER_HART; j++) {
    uint64_t size = get_allocation_size(hart_id, (uint64_t)iter, (uint64_t)j);
    void *ptr = malloc(size);
    if (ptr == 0) {
      return DIAG_FAILED;
    }
    memset(ptr, (int)hart_id, size);
    allocated[hart_id][iter][j] = ptr;
  }
  return DIAG_PASSED;
}

static int make_callocations(uint64_t hart_id, int iter) {
  for (int j = 0; j < ALLOCS_PER_HART; j++) {
    uint64_t size = get_allocation_size(hart_id, (uint64_t)iter, (uint64_t)j);
    void *ptr = calloc(1, size);
    if (ptr == 0) {
      return DIAG_FAILED;
    }
    memset(ptr, (int)hart_id, size);
    allocated[hart_id][iter][j] = ptr;
  }
  return DIAG_PASSED;
}

static int make_aligned_allocations(uint64_t hart_id, int iter) {
  for (int j = 0; j < ALLOCS_PER_HART; j++) {
    uint64_t size = get_allocation_size(hart_id, (uint64_t)iter, (uint64_t)j);
    uint64_t align = get_allocation_align(hart_id, (uint64_t)iter, (uint64_t)j);
    void *ptr = memalign(align, size);
    if (ptr == 0) {
      return DIAG_FAILED;
    }
    memset(ptr, (int)hart_id, size);
    allocated[hart_id][iter][j] = ptr;
  }
  return DIAG_PASSED;
}

static void cleanup_test(uint64_t hart_id) {
  for (int iter = 0; iter < NUM_INTERATIONS; iter++) {
    for (int j = 0; j < ALLOCS_PER_HART; j++) {
      free(allocated[hart_id][iter][j]);
    }
  }
  return;
}
// Free only some of the allocations to force uneven work across harts.
static void free_some_allocations(uint64_t hart_id, int iter) {
  for (int j = 0; j < ALLOCS_PER_HART; j++) {
    uint64_t hash = allocation_entropy(0, hart_id, (uint64_t)iter, (uint64_t)j);
    if (hash % 3 > 0) {
      free(allocated[hart_id][iter][j]);
    }
  }
  return;
}

static int test_allocations(uint64_t hart_id, int iter) {
  for (int j = 0; j < ALLOCS_PER_HART; j++) {
    uint8_t *ptr = (uint8_t *)allocated[hart_id][iter][j];
    uint64_t size = get_allocation_size(hart_id, (uint64_t)iter, (uint64_t)j);
    for (uint64_t x = 0; x < size; x++) {
      if (ptr[x] != hart_id) {
        return DIAG_FAILED;
      }
    }
  }
  return DIAG_PASSED;
}

static int test_malloc(uint64_t hart_id) {
  // Make sure all hart start at the same time
  sync_all_harts_from_smode();
  for (int i = 0; i < NUM_INTERATIONS; i++) {
    if (make_allocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    if (test_allocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    free_some_allocations(hart_id, i);
  }
  sync_all_harts_from_smode();
  cleanup_test(hart_id);
  return DIAG_PASSED;
}

static int test_calloc(uint64_t hart_id) {
  // Make sure all hart start at the same time
  sync_all_harts_from_smode();
  for (int i = 0; i < NUM_INTERATIONS; i++) {
    if (make_callocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    if (test_allocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    free_some_allocations(hart_id, i);
  }
  sync_all_harts_from_smode();
  cleanup_test(hart_id);
  return DIAG_PASSED;
}

static int test_memalign(uint64_t hart_id) {
  // Make sure all hart start at the same time
  sync_all_harts_from_smode();
  for (int i = 0; i < NUM_INTERATIONS; i++) {
    if (make_aligned_allocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    if (test_allocations(hart_id, i) == DIAG_FAILED) {
      return DIAG_FAILED;
    }
    free_some_allocations(hart_id, i);
  }
  sync_all_harts_from_smode();
  cleanup_test(hart_id);
  return DIAG_PASSED;
}

int main(void) {
  uint64_t hart_id = get_thread_attributes_hart_id_from_smode();
  if (hart_id > MAX_NUM_HARTS_SUPPORTED) {
    return DIAG_FAILED;
  }
  if (test_malloc(hart_id) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  if (test_calloc(hart_id) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  if (test_memalign(hart_id) == DIAG_FAILED) {
    return DIAG_FAILED;
  }
  return DIAG_PASSED;
}
