// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

int puts(const char *str);
int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
