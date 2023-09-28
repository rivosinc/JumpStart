// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <inttypes.h>

#define IMSIC_DISABLE_EIDELIVERY  0
#define IMSIC_ENABLE_EIDELIVERY   1

#define IMSIC_DISABLE_EITHRESHOLD 1
#define IMSIC_ENABLE_EITHRESHOLD  0

#define IMSIC_EIDELIVERY          0x70
#define IMSIC_EITHRESHOLD         0x72

#define IMSIC_EIP0                0x80
#define IMSIC_EIPx_BITS           32

#define IMSIC_EIE0                0xc0

typedef enum EIX_REG_TYPE {
  EIX_REG_PENDING,
  EIX_REG_ENABLED,
} eix_reg_type_t;

typedef enum REG_BIT_ACTION {
  REG_BIT_SET,
  REG_BIT_CLEAR,
} reg_bit_action_t;
