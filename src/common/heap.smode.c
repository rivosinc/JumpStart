/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

// SPDX-FileCopyrightText: 2016 by Lukasz Janyst <lukasz@jany.st>

#include "heap.smode.h"

#include <assert.h>
#include <stdbool.h>

#include "cpu_bits.h"
#include "jumpstart.h"
#include "lock.smode.h"
#include "tablewalk.smode.h"
#include "uart.smode.h"

#define MEMCHUNK_USED       0x8000000000000000ULL
#define MEMCHUNK_MAX_SIZE   (MEMCHUNK_USED - 1)

#define NUM_HEAPS_SUPPORTED 3

#define MEMCHUNK_USED       0x8000000000000000ULL
#define MEMCHUNK_MAX_SIZE   (MEMCHUNK_USED - 1)
#define MIN_HEAP_SEGMENT_BYTES                                                 \
  (PER_HEAP_ALLOCATION_METADATA_SIZE + MIN_HEAP_ALLOCATION_SIZE)

// Helper macro to align size to minimum allocation size
#define ALIGN_TO_MIN_ALLOC(size)                                               \
  ((((size - 1) >> __builtin_ctzll(MIN_HEAP_ALLOCATION_SIZE))                  \
    << __builtin_ctzll(MIN_HEAP_ALLOCATION_SIZE)) +                            \
   MIN_HEAP_ALLOCATION_SIZE)

static_assert(sizeof(memchunk) == PER_HEAP_ALLOCATION_METADATA_SIZE,
              "PER_HEAP_ALLOCATION_METADATA_SIZE mismatch");

//------------------------------------------------------------------------------
// Heap info struct
//------------------------------------------------------------------------------
struct heap_info {
  uint8_t backing_memory;
  uint8_t memory_type;
  memchunk *head;
  memchunk *last_allocated; // Track where we last allocated from
  size_t size;
  spinlock_t lock;
  volatile uint8_t setup_done;
};

__attr_privdata struct heap_info heaps[NUM_HEAPS_SUPPORTED] = {
    {BACKING_MEMORY_DDR, MEMORY_TYPE_WB, NULL, NULL, 0, 0, 0},
    {BACKING_MEMORY_DDR, MEMORY_TYPE_WC, NULL, NULL, 0, 0, 0},
    {BACKING_MEMORY_DDR, MEMORY_TYPE_UC, NULL, NULL, 0, 0, 0},
};

__attr_stext static struct heap_info *find_matching_heap(uint8_t backing_memory,
                                                         uint8_t memory_type) {
  for (int i = 0; i < NUM_HEAPS_SUPPORTED; i++) {
    if (heaps[i].backing_memory == backing_memory &&
        heaps[i].memory_type == memory_type) {
      return &heaps[i];
    }
  }
  return NULL;
}

__attr_stext bool is_valid_heap(uint8_t backing_memory, uint8_t memory_type) {
  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  return (target_heap != NULL && target_heap->setup_done &&
          target_heap->head != 0);
}

//------------------------------------------------------------------------------
// Helper functions to convert numeric values to readable strings
//------------------------------------------------------------------------------
__attr_stext const char *backing_memory_to_string(uint8_t backing_memory) {
  switch (backing_memory) {
  case BACKING_MEMORY_DDR:
    return "DDR";
  default:
    return "UNKNOWN";
  }
}

__attr_stext const char *memory_type_to_string(uint8_t memory_type) {
  switch (memory_type) {
  case MEMORY_TYPE_WB:
    return "WB";
  case MEMORY_TYPE_WC:
    return "WC";
  case MEMORY_TYPE_UC:
    return "UC";
  default:
    return "UNKNOWN";
  }
}

//------------------------------------------------------------------------------
// Allocate memory on the heap
//------------------------------------------------------------------------------
__attr_stext void *malloc_from_memory(size_t size, uint8_t backing_memory,
                                      uint8_t memory_type) {
  if (!is_valid_heap(backing_memory, memory_type)) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
    return 0;
  }
  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  if (size > MEMCHUNK_MAX_SIZE || size == 0) {
    printk("Error: Invalid size for malloc request\n");
    jumpstart_smode_fail();
    return 0;
  }
  void *result = 0;
  acquire_lock(&target_heap->lock);

  uint64_t alloc_size = ALIGN_TO_MIN_ALLOC(size);

  //----------------------------------------------------------------------------
  // Try to find a suitable chunk that is unused, starting from last allocation
  //----------------------------------------------------------------------------
  memchunk *start = target_heap->last_allocated
                        ? target_heap->last_allocated->next
                        : target_heap->head;
  if (!start)
    start = target_heap->head; // Wrap around if at end
  memchunk *chunk = start;

  // First try searching from last allocation to end
  while (chunk) {
    if (!(chunk->size & MEMCHUNK_USED) && chunk->size >= alloc_size) {
      break;
    }
    chunk = chunk->next;
  }

  // If not found, search from beginning to where we started
  if (!chunk && start != target_heap->head) {
    chunk = target_heap->head;
    while (chunk && chunk != start) {
      if (!(chunk->size & MEMCHUNK_USED) && chunk->size >= alloc_size) {
        break;
      }
      chunk = chunk->next;
    }
    // If we reached start without finding a chunk, set chunk to NULL
    if (chunk == start) {
      chunk = NULL;
    }
  }

  if (!chunk) {
    goto exit_malloc;
  }

  //----------------------------------------------------------------------------
  // Split the chunk if it's big enough to contain one more header and at
  // least 8 more bytes
  //----------------------------------------------------------------------------
  if (chunk->size >= alloc_size + MIN_HEAP_SEGMENT_BYTES) {
    memchunk *new_chunk =
        (memchunk *)((void *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE +
                     alloc_size);
    new_chunk->size =
        chunk->size - alloc_size - PER_HEAP_ALLOCATION_METADATA_SIZE;
    new_chunk->next = chunk->next;
    chunk->next = new_chunk;
    chunk->size = alloc_size;
  }

  //----------------------------------------------------------------------------
  // Mark the chunk as used, update last_allocated, and return the memory
  //----------------------------------------------------------------------------
  chunk->size |= MEMCHUNK_USED;
  target_heap->last_allocated = chunk;
  result = (void *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE;
exit_malloc:
  release_lock(&target_heap->lock);
  return result;
}

__attr_stext void free_from_memory(void *ptr, uint8_t backing_memory,
                                   uint8_t memory_type) {
  if (!ptr) {
    return;
  }

  if (!is_valid_heap(backing_memory, memory_type)) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
  }

  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);

  acquire_lock(&target_heap->lock);

  // Validate that ptr is within heap bounds
  memchunk *chunk =
      (memchunk *)((void *)ptr - PER_HEAP_ALLOCATION_METADATA_SIZE);
  if (chunk < target_heap->head || !target_heap->head) {
    printk("Error: Invalid free - address below heap start\n");
    goto exit_free;
  }

  // Verify this is actually a used chunk
  if (!(chunk->size & MEMCHUNK_USED)) {
    printk("Error: Double free detected\n");
    jumpstart_smode_fail();
  }

  // Basic sanity check on chunk size
  if ((chunk->size & MEMCHUNK_MAX_SIZE) > MEMCHUNK_MAX_SIZE) {
    printk("Error: Invalid chunk size in free\n");
    jumpstart_smode_fail();
  }

  // Mark the chunk as free
  chunk->size &= ~MEMCHUNK_USED;

  // Clear last_allocated if it points to the freed chunk
  if (target_heap->last_allocated == chunk) {
    target_heap->last_allocated = NULL;
  }

  // Coalesce with next chunk if it exists and is free
  if (chunk->next && !(chunk->next->size & MEMCHUNK_USED)) {
    chunk->size += chunk->next->size + PER_HEAP_ALLOCATION_METADATA_SIZE;
    chunk->next = chunk->next->next;
  }

  // Coalesce with previous chunk if it exists and is free
  memchunk *prev = target_heap->head;
  while (prev && prev->next != chunk) {
    prev = prev->next;
  }
  if (prev && !(prev->size & MEMCHUNK_USED)) {
    prev->size += chunk->size + PER_HEAP_ALLOCATION_METADATA_SIZE;
    prev->next = chunk->next;

    // We need chunk to set last_allocated if it's NULL.
    chunk = prev;
  }

  if (target_heap->last_allocated == NULL) {
    // We've cleared last_allocated because it was set to the freed chunk.
    // Look for the next allocated chunk after this one as replacement.
    // We need to do this after any coalescing operations so that we're only
    // assigning last_allocated to valid chunks.
    memchunk *next_allocated = chunk->next;
    while (next_allocated && !(next_allocated->size & MEMCHUNK_USED)) {
      next_allocated = next_allocated->next;
    }

    if (next_allocated) {
      // Found a next allocated chunk, use it
      target_heap->last_allocated = next_allocated;
    } else {
      // No next allocated chunk found, look backwards
      memchunk *prev = target_heap->head;
      memchunk *prev_allocated = NULL;
      while (prev && prev != chunk) {
        if (prev->size & MEMCHUNK_USED) {
          prev_allocated = prev;
        }
        prev = prev->next;
      }

      if (prev_allocated) {
        target_heap->last_allocated = prev_allocated;
      } else {
        // No allocated chunks found, set to NULL as fallback
        // This will cause the next allocation to start from head
        target_heap->last_allocated = NULL;
      }
    }
  }

exit_free:
  release_lock(&target_heap->lock);
}

//------------------------------------------------------------------------------
// Set up the heap
//------------------------------------------------------------------------------
__attr_stext void setup_heap(uint64_t heap_start, uint64_t heap_end,
                             uint8_t backing_memory, uint8_t memory_type) {
  disable_checktc();

  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  if (target_heap == NULL) {
    printk(
        "Error: No matching heap found for backing_memory=%d, memory_type=%d\n",
        backing_memory, memory_type);
    jumpstart_smode_fail();
  }

  if (target_heap->setup_done) {
    // Verify the heap address matches what was previously set up
    if (target_heap->head != (memchunk *)heap_start) {
      printk("Error: Heap already initialized at different address. "
             "Expected: 0x%lx, Got: 0x%lx\n",
             (uint64_t)target_heap->head, heap_start);
      jumpstart_smode_fail();
    }
    return;
  }

  acquire_lock(&target_heap->lock);

  // Prevent double initialization. A cpu might have been waiting for the lock
  // while the heap was initialized by another cpu.
  if (target_heap->setup_done == 0) {

    // Translate the start and end of the heap sanity check it's memory type.
    struct translation_info xlate_info;
    translate_VA(heap_start, &xlate_info);
    if (xlate_info.walk_successful == 0) {
      printk("Error: Unable to translate heap start address.\n");
      jumpstart_smode_fail();
    }

    if (xlate_info.xatp_mode != VM_1_10_MBARE) {
      // Only sanity check the memory type if the SATP mode is not Bare.

      // WB = PMA in PBMT
      // UC = IO in PBMT
      // WC = NC in PBMT
      if ((memory_type == MEMORY_TYPE_WB &&
           xlate_info.pbmt_mode != PTE_PBMT_PMA) ||
          (memory_type == MEMORY_TYPE_UC &&
           xlate_info.pbmt_mode != PTE_PBMT_IO) ||
          (memory_type == MEMORY_TYPE_WC &&
           xlate_info.pbmt_mode != PTE_PBMT_NC)) {
        printk("Error: Heap start address is not correct memory type.");
        jumpstart_smode_fail();
      }

      translate_VA(heap_end - 1, &xlate_info);
      if (xlate_info.walk_successful == 0) {
        printk("Error: Unable to translate heap end address.\n");
        jumpstart_smode_fail();
      }
      if ((memory_type == MEMORY_TYPE_WB &&
           xlate_info.pbmt_mode != PTE_PBMT_PMA) ||
          (memory_type == MEMORY_TYPE_UC &&
           xlate_info.pbmt_mode != PTE_PBMT_IO) ||
          (memory_type == MEMORY_TYPE_WC &&
           xlate_info.pbmt_mode != PTE_PBMT_NC)) {
        printk("Error: Heap end address is not correct memory type.");
        jumpstart_smode_fail();
      }
    }

    target_heap->head = (memchunk *)heap_start;
    target_heap->last_allocated = NULL; // Initialize last_allocated to NULL
    target_heap->head->next = NULL;
    target_heap->head->size =
        heap_end - heap_start - PER_HEAP_ALLOCATION_METADATA_SIZE;
    target_heap->size = heap_end - heap_start;

    target_heap->setup_done = 1;
  } else {
    // Verify the heap address matches what was previously set up
    if (target_heap->head != (memchunk *)heap_start) {
      printk("Error: Heap already initialized at different address. "
             "Expected: 0x%lx, Got: 0x%lx\n",
             (uint64_t)target_heap->head, heap_start);
      jumpstart_smode_fail();
    }
    if (target_heap->size != heap_end - heap_start) {
      printk("Error: Heap size mismatch. Expected: 0x%lx, Got: 0x%lx\n",
             target_heap->size, heap_end - heap_start);
      jumpstart_smode_fail();
    }
  }

  release_lock(&target_heap->lock);
  enable_checktc();
}

__attr_stext void deregister_heap(uint8_t backing_memory, uint8_t memory_type) {
  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  if (target_heap == NULL) {
    printk(
        "Error: No matching heap found for backing_memory=%d, memory_type=%d\n",
        backing_memory, memory_type);
    jumpstart_smode_fail();
  }

  if (target_heap->setup_done == 0) {
    return;
  }

  acquire_lock(&target_heap->lock);

  size_t size_of_all_chunks = 0;

  memchunk *chunk = target_heap->head;
  while (chunk) {
    if (chunk->size & MEMCHUNK_USED) {
      printk("Error: Chunk still in use\n");
      jumpstart_smode_fail();
    }
    size_of_all_chunks += chunk->size + PER_HEAP_ALLOCATION_METADATA_SIZE;
    chunk = chunk->next;
  }

  if (size_of_all_chunks != target_heap->size) {
    printk("Error: Heap size mismatch. Expected: 0x%lx, Got: 0x%lx\n",
           target_heap->size, size_of_all_chunks);
    jumpstart_smode_fail();
  }

  target_heap->setup_done = 0;
  target_heap->head = NULL;
  target_heap->last_allocated = NULL; // Clear last_allocated pointer
  target_heap->size = 0;
  release_lock(&target_heap->lock);
}

__attr_stext size_t get_heap_size(uint8_t backing_memory, uint8_t memory_type) {
  if (!is_valid_heap(backing_memory, memory_type)) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
    return 0;
  }
  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  if (target_heap == NULL) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
    return 0;
  }

  return target_heap->size;
}

__attr_stext void *calloc_from_memory(size_t nmemb, size_t size,
                                      uint8_t backing_memory,
                                      uint8_t memory_type) {
  uint8_t *data = malloc_from_memory(nmemb * size, backing_memory, memory_type);
  if (data) {
    for (size_t i = 0; i < nmemb * size; ++i) {
      *(data + i) = 0;
    }
  }
  return data;
}

__attr_stext void *memalign_from_memory(size_t alignment, size_t size,
                                        uint8_t backing_memory,
                                        uint8_t memory_type) {
  // Validate alignment is non-zero and a power of 2
  if (alignment == 0 || alignment & (alignment - 1)) {
    return 0;
  }

  if (!is_valid_heap(backing_memory, memory_type)) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
    return 0;
  }

  struct heap_info *target_heap =
      find_matching_heap(backing_memory, memory_type);
  if (target_heap == NULL) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(backing_memory),
           memory_type_to_string(memory_type));
    jumpstart_smode_fail();
    return 0;
  }

  if (size > MEMCHUNK_MAX_SIZE) {
    printk("Error: Invalid size for memalign request\n");
    jumpstart_smode_fail();
    return 0;
  }

  // For small alignments, use regular malloc since heap ensures
  // MIN_HEAP_ALLOCATION_SIZE alignment
  if (alignment <= MIN_HEAP_ALLOCATION_SIZE) {
    return malloc_from_memory(size, backing_memory, memory_type);
  }

  void *result = 0;
  acquire_lock(&target_heap->lock);

  uint64_t alloc_size = ALIGN_TO_MIN_ALLOC(size);

  //----------------------------------------------------------------------------
  // Try to find a suitable chunk that is unused
  //----------------------------------------------------------------------------
  uint64_t pow2 = (uint64_t)__builtin_ctzll((uint64_t)alignment);
  uint8_t aligned = 0;
  uint64_t aligned_start = 0, start = 0, end = 0;
  memchunk *chunk;
  for (chunk = target_heap->head; chunk; chunk = chunk->next) {
    // Skip if chunk is used or too small
    if (chunk->size & MEMCHUNK_USED || chunk->size < alloc_size) {
      continue;
    }

    // Calculate chunk boundaries
    start = (uint64_t)((char *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE);
    end = (uint64_t)((char *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE +
                     chunk->size);

    // First try: Check if chunk's start address can be used directly after
    // alignment
    aligned_start = (((start - 1) >> pow2) << pow2) + alignment;
    if (start == aligned_start) {
      // Current chunk is already properly aligned - use it as-is
      aligned = 1;
      break;
    }

    // Second try: Check if we can split this chunk to create an aligned
    // allocation We need space for: metadata + minimum allocation before the
    // aligned address
    aligned_start =
        ((((start + MIN_HEAP_SEGMENT_BYTES) - 1) >> pow2) << pow2) + alignment;

    // Verify the aligned address fits within the chunk
    if (aligned_start >= end) {
      continue;
    }

    // Verify there's enough space for the requested allocation
    if (aligned_start + alloc_size > end) {
      continue;
    }

    // Found a suitable chunk we can split
    break;
  }

  if (!chunk) {
    goto exit_memalign;
  }

  //----------------------------------------------------------------------------
  // Handle chunk allocation based on alignment result
  //----------------------------------------------------------------------------
  // If the chunk's start address is not naturally aligned, we need to split it:
  // 1. The first chunk contains the unaligned portion before aligned_start
  // 2. The second chunk starts at aligned_start and will be used for allocation
  // This ensures the allocated memory satisfies the alignment requirement while
  // preserving the rest of the chunk for future allocations
  if (!aligned) {
    memchunk *new_chunk =
        (memchunk *)((void *)aligned_start - PER_HEAP_ALLOCATION_METADATA_SIZE);
    new_chunk->size = end - aligned_start;
    new_chunk->next = chunk->next;
    chunk->size -= (new_chunk->size + PER_HEAP_ALLOCATION_METADATA_SIZE);
    chunk->next = new_chunk;
    chunk = chunk->next;
  }

  // Trim excess space from the aligned chunk if possible
  if (chunk->size >= alloc_size + MIN_HEAP_SEGMENT_BYTES) {
    memchunk *new_chunk =
        (memchunk *)((void *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE +
                     alloc_size);
    new_chunk->size =
        chunk->size - alloc_size - PER_HEAP_ALLOCATION_METADATA_SIZE;
    new_chunk->next = chunk->next;
    chunk->next = new_chunk;
    chunk->size = alloc_size;
  }

  //----------------------------------------------------------------------------
  // Finalize allocation
  //----------------------------------------------------------------------------
  chunk->size |= MEMCHUNK_USED;
  target_heap->last_allocated = chunk;
  result = (void *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE;

exit_memalign:
  release_lock(&target_heap->lock);
  return result;
}

__attr_stext void print_heap(void) {
  if (!is_valid_heap(BACKING_MEMORY_DDR, MEMORY_TYPE_WB)) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(BACKING_MEMORY_DDR),
           memory_type_to_string(MEMORY_TYPE_WB));
    jumpstart_smode_fail();
  }

  struct heap_info *target_heap =
      find_matching_heap(BACKING_MEMORY_DDR, MEMORY_TYPE_WB);
  if (target_heap == NULL) {
    printk("Error: Heap not initialized for %s/%s.\n",
           backing_memory_to_string(BACKING_MEMORY_DDR),
           memory_type_to_string(MEMORY_TYPE_WB));
    jumpstart_smode_fail();
    return;
  }

  acquire_lock(&target_heap->lock);
  printk("===================\n");
  memchunk *chunk = target_heap->head;
  while (chunk != 0) {
    if (chunk->size & MEMCHUNK_USED) {
      printk("[USED] Size:0x%llx\n", (chunk->size & MEMCHUNK_MAX_SIZE));
    } else {
      printk("[FREE] Size:0x%lx    Start:0x%lx\n", chunk->size,
             (uint64_t)((void *)chunk + PER_HEAP_ALLOCATION_METADATA_SIZE));
    }
    chunk = chunk->next;
  }

  printk("===================\n");
  release_lock(&target_heap->lock);
}

// The default versions of the functions use the DDR and WB memory type.
__attr_stext void *malloc(size_t size) {
  return malloc_from_memory(size, BACKING_MEMORY_DDR, MEMORY_TYPE_WB);
}

__attr_stext void free(void *ptr) {
  free_from_memory(ptr, BACKING_MEMORY_DDR, MEMORY_TYPE_WB);
}

__attr_stext void *calloc(size_t nmemb, size_t size) {
  return calloc_from_memory(nmemb, size, BACKING_MEMORY_DDR, MEMORY_TYPE_WB);
}

__attr_stext void *memalign(size_t alignment, size_t size) {
  return memalign_from_memory(alignment, size, BACKING_MEMORY_DDR,
                              MEMORY_TYPE_WB);
}

__attr_stext void *memset(void *s, int c, size_t n) {
  uint8_t *p = s;
  for (size_t i = 0; i < n; i++) {
    *(p++) = (uint8_t)c;
  }
  return s;
}

__attr_stext void *memcpy(void *dest, const void *src, size_t n) {
  size_t numQwords = n / 8;
  size_t remindingBytes = n % 8;

  uint64_t *d64 = dest;
  const uint64_t *s64 = src;
  for (size_t i = 0; i < numQwords; ++i) {
    *(d64++) = *(s64++);
  }

  uint8_t *d8 = (uint8_t *)d64;
  const uint8_t *s8 = (const uint8_t *)s64;
  for (size_t i = 0; i < remindingBytes; ++i) {
    *(d8++) = *(s8++);
  }

  return dest;
}
