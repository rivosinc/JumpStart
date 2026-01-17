/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "uart.mmode.h"
#include "jumpstart.h"
#include "lock.mmode.h"
#include "uart.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>

extern void m_putch(char c);

void m_mark_uart_as_enabled(void);

__attribute__((
    section(".jumpstart.cpu.data.privileged"))) static volatile uint8_t
    uart_initialized = 0;

__attr_mtext void m_mark_uart_as_enabled(void) {
  uart_initialized = 1;
}

__attr_mtext int m_is_uart_enabled(void) {
  return uart_initialized == 1;
}

__attr_mtext int m_puts(const char *str) {
  return _puts(uart_initialized, m_putch, str);
}
