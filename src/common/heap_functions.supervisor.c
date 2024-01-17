// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "heap_functions.supervisor.h"

#include "jumpstart_defines.h"

#include <stdint.h>

extern uint64_t _JUMPSTART_SUPERVISOR_HEAP_START[];
extern uint64_t _JUMPSTART_SUPERVISOR_HEAP_END[];

void setup_heap(void);
//------------------------------------------------------------------------------
// Malloc helper structs
//------------------------------------------------------------------------------
struct memchunk {
  struct memchunk *next;
  uint64_t size;
};

typedef struct memchunk memchunk;

__attribute__((section(".jumpstart.data.supervisor"))) static memchunk *head;
#define MEMCHUNK_USED     0x8000000000000000ULL
#define MEMCHUNK_MAX_SIZE (MEMCHUNK_USED - 1)
//------------------------------------------------------------------------------
// Allocate memory on the heap
//------------------------------------------------------------------------------
__attribute__((section(".jumpstart.text.supervisor"))) void *
malloc(size_t size) {
  if (head == 0 || size > MEMCHUNK_MAX_SIZE) {
    return 0;
  }

  //----------------------------------------------------------------------------
  // Allocating anything less than 8 bytes is kind of pointless, the
  // book-keeping overhead is too big.
  //----------------------------------------------------------------------------
  uint64_t alloc_size = (((size - 1) >> 3) << 3) + 8;

  //----------------------------------------------------------------------------
  // Try to find a suitable chunk that is unused
  //----------------------------------------------------------------------------
  memchunk *chunk = head;
  while (chunk) {
    if (!(chunk->size & MEMCHUNK_USED) && chunk->size >= alloc_size) {
      break;
    }
    chunk = chunk->next;
  }

  if (!chunk) {
    return 0;
  }

  //----------------------------------------------------------------------------
  // Split the chunk if it's big enough to contain one more header and at
  // least 8 more bytes
  //----------------------------------------------------------------------------
  if (chunk->size > alloc_size + sizeof(memchunk) + 8) {
    memchunk *new_chunk =
        (memchunk *)((void *)chunk + sizeof(memchunk) + alloc_size);
    new_chunk->size = chunk->size - alloc_size - sizeof(memchunk);
    new_chunk->next = chunk->next;
    chunk->next = new_chunk;
    chunk->size = alloc_size;
  }

  //----------------------------------------------------------------------------
  // Mark the chunk as used and return the memory
  //----------------------------------------------------------------------------
  chunk->size |= MEMCHUNK_USED;
  return (void *)chunk + sizeof(memchunk);
}

//------------------------------------------------------------------------------
// Free the memory
//------------------------------------------------------------------------------
__attribute__((section(".jumpstart.text.supervisor"))) void free(void *ptr) {
  if (!ptr) {
    return;
  }

  memchunk *chunk = (memchunk *)((void *)ptr - sizeof(memchunk));
  chunk->size &= ~MEMCHUNK_USED;
}

//------------------------------------------------------------------------------
// Set up the heap
//------------------------------------------------------------------------------
__attribute__((section(".jumpstart.text.machine"))) void setup_heap(void) {
  uint64_t *heap_start = (uint64_t *)&_JUMPSTART_SUPERVISOR_HEAP_START;
  uint64_t *heap_end = (uint64_t *)&_JUMPSTART_SUPERVISOR_HEAP_END;

  head = (memchunk *)heap_start;
  head->next = NULL;
  head->size =
      (uint64_t)heap_end - (uint64_t)heap_start - (uint64_t)sizeof(memchunk);
}

__attribute__((section(".jumpstart.text.supervisor"))) void *
calloc(size_t nmemb, size_t size) {
  uint8_t *data = malloc(nmemb * size);
  for (size_t i = 0; i < nmemb * size; ++i) {
    data[i] = 0;
  }
  return data;
}

__attribute__((section(".jumpstart.text.supervisor"))) void *
memalign(size_t alignment, size_t size) {
  if (head == 0 || size > MEMCHUNK_MAX_SIZE) {
    return 0;
  }

  if (alignment <= 8) {
    return malloc(size);
  }

  //----------------------------------------------------------------------------
  // Allocating anything less than 8 bytes is kind of pointless, the
  // book-keeping overhead is too big.
  //----------------------------------------------------------------------------
  uint64_t alloc_size = (((size - 1) >> 3) << 3) + 8;

  //----------------------------------------------------------------------------
  // Try to find a suitable chunk that is unused
  //----------------------------------------------------------------------------
  uint64_t pow2 = (uint64_t)__builtin_ctzll((uint64_t)alignment);
  uint8_t aligned = 0;
  uint64_t aligned_start = 0, start = 0, end = 0;
  memchunk *chunk;
  for (chunk = head; chunk; chunk = chunk->next) {
    // Chunk used
    if (chunk->size & MEMCHUNK_USED) {
      continue;
    }

    // Chunk too small
    if (chunk->size < alloc_size) {
      continue;
    }

    start = (uint64_t)((char *)chunk + sizeof(memchunk));
    end = (uint64_t)((char *)chunk + sizeof(memchunk) + chunk->size);
    aligned_start = (((start - 1) >> pow2) << pow2) + alignment;

    // The current chunk is already aligned so just allocate it
    if (start == aligned_start) {
      aligned = 1;
      break;
    }

    // Aligned start must be within the chunk
    if (aligned_start >= end) {
      continue;
    }

    // The start of the allocated chunk must be far away from the start of
    // the current chunk to leave space for at least 8 bytes of data payload
    // and metadata of the new chunk
    if (aligned_start < start + sizeof(memchunk) + 8) {
      continue;
    }

    // The current chunk is too small
    if (aligned_start + alloc_size > end) {
      continue;
    }

    break;
  }

  if (!chunk) {
    return 0;
  }

  // If chunk is not aligned we need to allecate a new chunk just before it
  if (!aligned) {
    memchunk *new_chunk =
        (memchunk *)((void *)aligned_start - sizeof(memchunk));
    new_chunk->size = end - aligned_start;
    new_chunk->next = chunk->next;
    chunk->size -= (new_chunk->size + sizeof(memchunk));
    chunk->next = new_chunk;
    chunk = chunk->next;
  }

  // If the chunk needs to be trimmed
  if (chunk->size > alloc_size + sizeof(memchunk) + 8) {
    memchunk *new_chunk =
        (memchunk *)((void *)chunk + sizeof(memchunk) + alloc_size);
    new_chunk->size = chunk->size - alloc_size - sizeof(memchunk);
    new_chunk->next = chunk->next;
    chunk->next = new_chunk;
    chunk->size = alloc_size;
  }
  chunk->size |= MEMCHUNK_USED;
  return (void *)chunk + sizeof(memchunk);
}

__attribute__((section(".jumpstart.text.supervisor"))) void *
memset(void *s, int c, size_t n) {
  uint8_t *p = s;
  for (size_t i = 0; i < n; i++) {
    *(p++) = (uint8_t)c;
  }
  return s;
}

__attribute__((section(".jumpstart.text.supervisor"))) void *
memcpy(void *dest, const void *src, size_t n) {
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
