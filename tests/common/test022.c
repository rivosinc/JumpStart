// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "jumpstart_functions.h"

__attribute__((const)) int main(void);

int main(void) {
  jumpstart_supervisor_fail();
}