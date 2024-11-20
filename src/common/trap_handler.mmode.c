// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

__attr_mtext void
register_mmode_trap_handler_override(uint64_t mcause,
                                     uint64_t handler_address) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_mmode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_MMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_mmode_fail();
    }

    trap_overrides->mmode_interrupt_handler_overrides[exception_code] =
        handler_address;
  } else {
    if (exception_code >= NUM_MMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_mmode_fail();
    }

    trap_overrides->mmode_exception_handler_overrides[exception_code] =
        handler_address;
  }
}

__attr_mtext void deregister_mmode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_mmode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_MMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_mmode_fail();
    }

    if (trap_overrides->mmode_interrupt_handler_overrides[exception_code] ==
        0x0) {
      jumpstart_mmode_fail();
    }

    trap_overrides->mmode_interrupt_handler_overrides[exception_code] = 0x0;
  } else {
    if (exception_code >= NUM_MMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_mmode_fail();
    }

    if (trap_overrides->mmode_exception_handler_overrides[exception_code] ==
        0) {
      jumpstart_mmode_fail();
    }

    trap_overrides->mmode_exception_handler_overrides[exception_code] = 0x0;
  }
}

__attr_mtext uint64_t get_mmode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_mmode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_MMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_mmode_fail();
    }

    return trap_overrides->mmode_interrupt_handler_overrides[exception_code];
  }

  if (exception_code >= NUM_MMODE_EXCEPTION_HANDLER_OVERRIDES) {
    jumpstart_mmode_fail();
  }

  return trap_overrides->mmode_exception_handler_overrides[exception_code];
}
