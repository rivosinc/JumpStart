/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#define _puts(__uart_initialized, __putch, __str)                              \
  ({                                                                           \
    if (__uart_initialized == 0) {                                             \
      return 0;                                                                \
    }                                                                          \
                                                                               \
    int __count = 0;                                                           \
                                                                               \
    while (*__str != '\0') {                                                   \
      __putch(*__str);                                                         \
      __count++;                                                               \
      __str++;                                                                 \
    }                                                                          \
                                                                               \
    __count;                                                                   \
  })

#define VPRINTK_BUFFER_SIZE 1024

#define _vprintk(__puts, __fmt, __args)                                        \
  ({                                                                           \
    static char __buf[VPRINTK_BUFFER_SIZE];                                    \
    int __rc, __ret;                                                           \
    __rc = vsnprintf(__buf, sizeof(__buf), __fmt, __args);                     \
    if (__rc > (int)sizeof(__buf)) {                                           \
      __puts("vprintk() buffer overflow\n");                                   \
      __ret = -1;                                                              \
    } else {                                                                   \
      __ret = __puts(__buf);                                                   \
    }                                                                          \
    __ret;                                                                     \
  })

#define _printk(__printk_lock, __acquire_lock, __release_lock,                 \
                __uart_initialized, _vprintk, __fmt)                           \
  ({                                                                           \
    if (__uart_initialized == 0) {                                             \
      return 0;                                                                \
    }                                                                          \
    va_list __args;                                                            \
    int __rc;                                                                  \
    __acquire_lock(&__printk_lock);                                            \
    va_start(__args, __fmt);                                                   \
    __rc = _vprintk(__fmt, __args);                                            \
    va_end(__args);                                                            \
    __release_lock(&__printk_lock);                                            \
                                                                               \
    __rc;                                                                      \
  })
