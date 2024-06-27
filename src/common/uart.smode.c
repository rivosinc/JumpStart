// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "uart.smode.h"
#include "jumpstart.h"
#include "jumpstart_defines.h"
#include "lock.smode.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>

extern void putch(char c);

int toupper(int c);
static int vprintk(const char *fmt, va_list args)
    __attribute__((format(printf, 1, 0)))
    __attribute__((section(".jumpstart.text.smode")));
void mark_uart_as_enabled(void);

__attribute__((
    section(".jumpstart.data.smode"))) static uint8_t uart_initialized = 0;

__attribute__((
    section(".jumpstart.data.smode"))) static spinlock_t printk_lock = 0;

__attribute__((section(".jumpstart.text.smode"))) void
mark_uart_as_enabled(void) {
  uart_initialized = 1;
}

__attribute__((section(".jumpstart.text.smode"))) int puts(const char *str) {
  if (uart_initialized == 0) {
    jumpstart_smode_fail();
  }

  int count = 0;

  while (*str != '\0') {
    putch(*str);
    count++;
    str++;
  }

  return count;
}

#define VPRINTK_BUFFER_SIZE 1024

static int vprintk(const char *fmt, va_list args) {
  static char buf[VPRINTK_BUFFER_SIZE];
  int rc;

  rc = vsnprintf(buf, sizeof(buf), fmt, args);

  if (rc > (int)sizeof(buf)) {
    puts("vprintk() buffer overflow\n");
    return -1;
  }

  return puts(buf);
}

__attribute__((section(".jumpstart.text.smode"))) int printk(const char *fmt,
                                                             ...) {
  if (uart_initialized == 0) {
    return 0;
  }

  va_list args;
  int rc;

  acquire_lock(&printk_lock);

  va_start(args, fmt);
  rc = vprintk(fmt, args);
  va_end(args);

  release_lock(&printk_lock);

  return rc;
}
