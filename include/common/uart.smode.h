// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

int puts(const char *str);
int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

#ifdef NDEBUG
#define pr_debug(...)
#else
#define pr_debug(...) printk(__VA_ARGS__)
#endif
