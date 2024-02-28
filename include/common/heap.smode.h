// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <stddef.h>

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
