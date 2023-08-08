// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "stdarg.h"
#include "stddef.h"
#include <inttypes.h>

int snprintf(char *buf, size_t size, const char *fmt, ...)
    __attribute__((section(".jumpstart.text.supervisor")));
int vsnprintf(char *str, size_t size, char const *fmt, va_list ap)
    __attribute__((section(".jumpstart.text.supervisor")));
size_t strlen(const char *str)
    __attribute__((section(".jumpstart.text.supervisor")));
int toupper(int c) __attribute__((section(".jumpstart.text.supervisor")));
