// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

void setup_uart(void);
int puts(const char *str);
int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
