// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "stdarg.h"
#include "stddef.h"
#include <inttypes.h>

int snprintf(char *buf, size_t size, const char *fmt, ...);
int vsnprintf(char *str, size_t size, char const *fmt, va_list ap);
size_t strlen(const char *str);
int toupper(int c);
