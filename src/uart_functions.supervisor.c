// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "uart_functions.supervisor.h"

#include "jumpstart_defines.h"

#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>

int toupper(int c);

static int vprintk(const char *fmt, va_list args)
    __attribute__((format(printf, 1, 0)))
    __attribute__((section(".jumpstart.text.supervisor")));

static void putch(char c)
    __attribute__((section(".jumpstart.text.supervisor")));

__attribute__((section(".jumpstart.text.supervisor"))) void setup_uart(void) {
  volatile uint32_t *uart_ctrl =
      (uint32_t *)((uint32_t)OT_UART_BASE + OT_UART_CTRL);
  volatile uint32_t uart_init = (OT_UART_CTRL_TXEN | OT_UART_CTRL_RXEN);

  *uart_ctrl = uart_init;
}

static void putch(char c) {
  volatile uint32_t *uart_status =
      (uint32_t *)((uint32_t)OT_UART_BASE + OT_UART_STATUS);
  volatile uint32_t *uart_wrdata =
      (uint32_t *)((uint32_t)OT_UART_BASE + OT_UART_WDATA);
  /* check for status not full */
  do {
  } while ((*uart_status & OT_UART_STATUS_TXFULL));

  /* place the character */
  *uart_wrdata = (uint32_t)c;
}

__attribute__((section(".jumpstart.text.supervisor"))) int
puts(const char *str) {
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

__attribute__((section(".jumpstart.text.supervisor"))) int
printk(const char *fmt, ...) {
  va_list args;
  int rc;

  va_start(args, fmt);
  rc = vprintk(fmt, args);
  va_end(args);

  return rc;
}
