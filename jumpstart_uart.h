// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

void setup_uart(void) __attribute__((section(".jumpstart.text")));
int puts(const char *str) __attribute__((section(".jumpstart.text")));
int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)))
__attribute__((section(".jumpstart.text")));
