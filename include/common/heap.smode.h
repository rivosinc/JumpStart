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
// Malloc helper structs
//------------------------------------------------------------------------------
struct memchunk {
  struct memchunk *next;
  uint64_t size;
};

typedef struct memchunk memchunk;

//------------------------------------------------------------------------------
// Heap Constants
//------------------------------------------------------------------------------
// Allocating anything less than 8 bytes is kind of pointless, the
// book-keeping overhead is too big.
//------------------------------------------------------------------------------
#define MIN_HEAP_ALLOCATION_SIZE 8
#define PER_HEAP_ALLOCATION_METADATA_SIZE                                      \
  sizeof(struct memchunk) // Per allocation metadata size

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
