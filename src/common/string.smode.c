// SPDX-FileCopyrightText: 1990 - 2011 The FreeBSD Foundation
// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <inttypes.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

int toupper(int c);

static char *ksprintn(char *nbuf, uintmax_t num, int base, int *lenp, int upper)
    __attribute__((section(".jumpstart.text.smode")));

int islower(int c) __attribute__((section(".jumpstart.text.smode")));
int isupper(int c) __attribute__((section(".jumpstart.text.smode")));
int tolower(int c) __attribute__((section(".jumpstart.text.smode")));

inline int islower(int c) {
  return c >= 'a' && c <= 'z';
}

inline int isupper(int c) {
  return c >= 'A' && c <= 'Z';
}

inline int tolower(int c) {
  return isupper(c) ? c - ('A' - 'a') : c;
}

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wsuggest-attribute=const"
__attribute__((section(".jumpstart.text.smode"))) int toupper(int c) {
  return islower(c) ? c + ('A' - 'a') : c;
}
#pragma GCC diagnostic pop

__attribute__((section(".jumpstart.text.smode"))) size_t
strlen(const char *str) {
  size_t len = 0;

  while (str[len])
    len++;

  return len;
}

static char const hex2ascii_data[] = "0123456789abcdefghijklmnopqrstuvwxyz";

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wsign-conversion"
#pragma GCC diagnostic ignored "-Wconversion"
#pragma GCC diagnostic ignored "-Wstrict-overflow"

/*
 * Put a NUL-terminated ASCII number (base <= 36) in a buffer in reverse
 * order; return an optional length and a pointer to the last character
 * written in the buffer (i.e., the first character of the string).
 * The buffer pointed to by `nbuf' must have length >= MAXNBUF.
 */
static char *ksprintn(char *nbuf, uintmax_t num, int base, int *lenp,
                      int upper) {
  char *p, c;

  p = nbuf;
  *p = '\0';
  do {
    c = hex2ascii_data[num % base];
    *++p = upper ? toupper(c) : c;
  } while (num /= base);
  if (lenp)
    *lenp = p - nbuf;
  return (p);
}

/*
 * Scaled down version of printf(3).
 */
__attribute__((section(".jumpstart.text.smode"))) int
vsnprintf(char *str, size_t size, char const *fmt, va_list ap) {
#define PCHAR(c)                                                               \
  do {                                                                         \
    if (size >= 2) {                                                           \
      *str++ = c;                                                              \
      size--;                                                                  \
    }                                                                          \
    retval++;                                                                  \
  } while (0)

#define MAXNBUF 65
  char nbuf[MAXNBUF];
  const char *p, *percent;
  int ch, n;
  uint64_t num;
  int base, lflag, qflag, tmp, width, ladjust, sharpflag, neg, sign, dot;
  int cflag, hflag, jflag, tflag, zflag;
  int dwidth, upper;
  char padc;
  int stop = 0, retval = 0;

  num = 0;

  for (;;) {
    padc = ' ';
    width = 0;
    while ((ch = (unsigned char)*fmt++) != '%' || stop) {
      if (ch == '\0') {
        if (size >= 1)
          *str++ = '\0';
        return (retval);
      }
      PCHAR(ch);
    }
    percent = fmt - 1;
    qflag = 0;
    lflag = 0;
    ladjust = 0;
    sharpflag = 0;
    neg = 0;
    sign = 0;
    dot = 0;
    dwidth = 0;
    upper = 0;
    cflag = 0;
    hflag = 0;
    jflag = 0;
    tflag = 0;
    zflag = 0;
  reswitch:
    switch (ch = (unsigned char)*fmt++) {
    case '.':
      dot = 1;
      goto reswitch;
    case '#':
      sharpflag = 1;
      goto reswitch;
    case '+':
      sign = 1;
      goto reswitch;
    case '-':
      ladjust = 1;
      goto reswitch;
    case '%':
      PCHAR(ch);
      break;
    case '*':
      if (!dot) {
        width = va_arg(ap, int);
        if (width < 0) {
          ladjust = !ladjust;
          width = -width;
        }
      } else {
        dwidth = va_arg(ap, int);
      }
      goto reswitch;
    case '0':
      if (!dot) {
        padc = '0';
        goto reswitch;
      }
      __attribute__((fallthrough));
    case '1':
      __attribute__((fallthrough));
    case '2':
      __attribute__((fallthrough));
    case '3':
      __attribute__((fallthrough));
    case '4':
      __attribute__((fallthrough));
    case '5':
      __attribute__((fallthrough));
    case '6':
      __attribute__((fallthrough));
    case '7':
      __attribute__((fallthrough));
    case '8':
      __attribute__((fallthrough));
    case '9':
      for (n = 0;; ++fmt) {
        n = n * 10 + ch - '0';
        ch = *fmt;
        if (ch < '0' || ch > '9')
          break;
      }
      if (dot)
        dwidth = n;
      else
        width = n;
      goto reswitch;
    case 'c':
      PCHAR(va_arg(ap, int));
      break;
    case 'd':
    case 'i':
      base = 10;
      sign = 1;
      goto handle_sign;
    case 'h':
      if (hflag) {
        hflag = 0;
        cflag = 1;
      } else
        hflag = 1;
      goto reswitch;
    case 'j':
      jflag = 1;
      goto reswitch;
    case 'l':
      if (lflag) {
        lflag = 0;
        qflag = 1;
      } else
        lflag = 1;
      goto reswitch;
    case 'n':
      if (jflag)
        *(va_arg(ap, intmax_t *)) = retval;
      else if (qflag)
        *(va_arg(ap, int64_t *)) = retval;
      else if (lflag)
        *(va_arg(ap, long *)) = retval;
      else if (zflag)
        *(va_arg(ap, size_t *)) = retval;
      else if (hflag)
        *(va_arg(ap, short *)) = retval;
      else if (cflag)
        *(va_arg(ap, char *)) = retval;
      else
        *(va_arg(ap, int *)) = retval;
      break;
    case 'o':
      base = 8;
      goto handle_nosign;
    case 'p':
      base = 16;
      sharpflag = (width == 0);
      sign = 0;
      num = (uintptr_t)va_arg(ap, void *);
      goto number;
    case 'q':
      qflag = 1;
      goto reswitch;
    case 'r':
      base = 10;
      if (sign)
        goto handle_sign;
      goto handle_nosign;
    case 's':
      p = va_arg(ap, char *);
      if (p == NULL)
        p = "(null)";
      if (!dot)
        n = strlen(p);
      else
        for (n = 0; n < dwidth && p[n]; n++)
          continue;

      width -= n;

      if (!ladjust && width > 0)
        while (width--)
          PCHAR(padc);
      while (n--)
        PCHAR(*p++);
      if (ladjust && width > 0)
        while (width--)
          PCHAR(padc);
      break;
    case 't':
      tflag = 1;
      goto reswitch;
    case 'u':
      base = 10;
      goto handle_nosign;
    case 'X':
      upper = 1;
      __attribute__((fallthrough));
    case 'x':
      base = 16;
      goto handle_nosign;
    case 'y':
      base = 16;
      sign = 1;
      goto handle_sign;
    case 'z':
      zflag = 1;
      goto reswitch;
    handle_nosign:
      sign = 0;
      if (jflag)
        num = va_arg(ap, uintmax_t);
      else if (qflag)
        num = va_arg(ap, uint64_t);
      else if (tflag)
        num = va_arg(ap, ptrdiff_t);
      else if (lflag)
        num = va_arg(ap, unsigned long);
      else if (zflag)
        num = va_arg(ap, size_t);
      else if (hflag)
        num = (unsigned short)va_arg(ap, int);
      else if (cflag)
        num = (unsigned char)va_arg(ap, int);
      else
        num = va_arg(ap, unsigned int);
      goto number;
    handle_sign:
      if (jflag)
        num = va_arg(ap, intmax_t);
      else if (qflag)
        num = va_arg(ap, int64_t);
      else if (tflag)
        num = va_arg(ap, ptrdiff_t);
      else if (lflag)
        num = va_arg(ap, long);
      else if (zflag)
        num = va_arg(ap, long);
      else if (hflag)
        num = (short)va_arg(ap, int);
      else if (cflag)
        num = (char)va_arg(ap, int);
      else
        num = va_arg(ap, int);
    number:
      if (sign && (intmax_t)num < 0) {
        neg = 1;
        num = -(intmax_t)num;
      }
      p = ksprintn(nbuf, num, base, &n, upper);
      tmp = 0;
      if (sharpflag && num != 0) {
        if (base == 8)
          tmp++;
        else if (base == 16)
          tmp += 2;
      }
      if (neg)
        tmp++;

      if (!ladjust && padc == '0')
        dwidth = width - tmp;
      width -= tmp + (dwidth > n ? dwidth : n);
      dwidth -= n;
      if (!ladjust)
        while (width-- > 0)
          PCHAR(' ');
      if (neg)
        PCHAR('-');
      if (sharpflag && num != 0) {
        if (base == 8) {
          PCHAR('0');
        } else if (base == 16) {
          PCHAR('0');
          PCHAR('x');
        }
      }
      while (dwidth-- > 0)
        PCHAR('0');

      while (*p)
        PCHAR(*p--);

      if (ladjust)
        while (width-- > 0)
          PCHAR(' ');

      break;
    default:
      while (percent < fmt)
        PCHAR(*percent++);
      /*
       * Since we ignore a formatting argument it is no
       * longer safe to obey the remaining formatting
       * arguments as the arguments will no longer match
       * the format specs.
       */
      stop = 1;
      break;
    }
  }
#undef PCHAR
}

#pragma GCC diagnostic pop

__attribute__((section(".jumpstart.text.smode"))) int
snprintf(char *buf, size_t size, const char *fmt, ...) {
  va_list args;
  int retval = 0;

  va_start(args, fmt);
  retval = vsnprintf(buf, size, fmt, args);
  va_end(args);

  return retval;
}
