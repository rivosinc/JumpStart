/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

// SPDX-FileCopyrightText: 2016 by Lukasz Janyst <lukasz@jany.st>

#pragma once

#include <stddef.h>
#include <stdint.h>

//------------------------------------------------------------------------------
// Heap Constants
//------------------------------------------------------------------------------
// Allocating anything less than 8 bytes is kind of pointless, the
// book-keeping overhead is too big.
//------------------------------------------------------------------------------
#define MIN_HEAP_ALLOCATION_BYTES 8
#define MEMCHUNK_SIZE             16 // Size of internal memchunk structure
#define MIN_HEAP_SEGMENT_BYTES    (MEMCHUNK_SIZE + MIN_HEAP_ALLOCATION_BYTES)
#define MEMCHUNK_USED             0x8000000000000000ULL
#define MEMCHUNK_MAX_SIZE         (MEMCHUNK_USED - 1)

// Helper macro to align size to minimum allocation size
#define ALIGN_TO_MIN_ALLOC(size)                                               \
  ((((size - 1) >> __builtin_ctzll(MIN_HEAP_ALLOCATION_BYTES))                 \
    << __builtin_ctzll(MIN_HEAP_ALLOCATION_BYTES)) +                           \
   MIN_HEAP_ALLOCATION_BYTES)

//------------------------------------------------------------------------------
//! Allocate memory on the heap
//------------------------------------------------------------------------------
void *malloc(size_t size);

//------------------------------------------------------------------------------
//! Free the memory
//------------------------------------------------------------------------------
void free(void *ptr);

void *calloc(size_t nmemb, size_t size);

void *memalign(size_t alignment, size_t size);

void *memset(void *s, int c, size_t n);

void *memcpy(void *dest, const void *src, size_t n);

//------------------------------------------------------------------------------
//! Debug Features
//------------------------------------------------------------------------------
void print_heap(void);

//------------------------------------------------------------------------------
// Memory type and backing memory specific versions
//------------------------------------------------------------------------------
void *malloc_from_memory(size_t size, uint8_t backing_memory,
                         uint8_t memory_type);

void free_from_memory(void *ptr, uint8_t backing_memory, uint8_t memory_type);

void *calloc_from_memory(size_t nmemb, size_t size, uint8_t backing_memory,
                         uint8_t memory_type);

void *memalign_from_memory(size_t alignment, size_t size,
                           uint8_t backing_memory, uint8_t memory_type);

void setup_heap(uint64_t heap_start, uint64_t heap_end, uint8_t backing_memory,
                uint8_t memory_type);

void deregister_heap(uint8_t backing_memory, uint8_t memory_type);

size_t get_heap_size(uint8_t backing_memory, uint8_t memory_type);
