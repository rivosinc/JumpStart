/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "uart.smode.h"
#include "jumpstart.h"
#include "lock.smode.h"
#include "uart.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>

int toupper(int c);
static int vprintk(const char *fmt, va_list args)
    __attribute__((format(printf, 1, 0))) __attr_stext;
void mark_uart_as_enabled(void);

__attribute__((
    section(".jumpstart.cpu.data.privileged"))) static volatile uint8_t
    uart_initialized = 0;

__attr_privdata static spinlock_t printk_lock = 0;

__attr_stext void mark_uart_as_enabled(void) {
  uart_initialized = 1;
}

__attr_stext int is_uart_enabled(void) {
  return uart_initialized == 1;
}

__attr_stext int puts(const char *str) {
  return _puts(uart_initialized, putch, str);
}

#define VPRINTK_BUFFER_SIZE 1024

static int vprintk(const char *fmt, va_list args) {
  return _vprintk(puts, fmt, args);
}

__attr_stext int printk(const char *fmt, ...) {
  return _printk(printk_lock, acquire_lock, release_lock, uart_initialized,
                 vprintk, fmt);
}
