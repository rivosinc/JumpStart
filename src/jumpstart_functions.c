// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#include "jumpstart_functions.h"

void register_trap_handler_override(uint8_t mode, uint64_t mcause,
                                    uint64_t handler_address) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_supervisor_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause >> MCAUSE_INTERRUPT_BIT_LSB;

  if (mode == MACHINE_MODE_ENCODING) {
    if (interrupt == 1) {
      if (exception_code >= NUM_MACHINE_MODE_INTERRUPT_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      trap_overrides->machine_mode_interrupt_handler_overrides[exception_code] =
          handler_address;
    } else {
      if (exception_code >= NUM_MACHINE_MODE_EXCEPTION_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      trap_overrides->machine_mode_exception_handler_overrides[exception_code] =
          handler_address;
    }
  } else if (mode == SUPERVISOR_MODE_ENCODING) {
    if (interrupt == 1) {
      if (exception_code >= NUM_SUPERVISOR_MODE_INTERRUPT_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      trap_overrides
          ->supervisor_mode_interrupt_handler_overrides[exception_code] =
          handler_address;
    } else {
      if (exception_code >= NUM_SUPERVISOR_MODE_EXCEPTION_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      trap_overrides
          ->supervisor_mode_exception_handler_overrides[exception_code] =
          handler_address;
    }
  } else {
    jumpstart_supervisor_fail();
  }
}

uint64_t get_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_supervisor_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint8_t mode = get_thread_attributes_current_mode_from_supervisor_mode();
  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause >> MCAUSE_INTERRUPT_BIT_LSB;

  if (mode == MACHINE_MODE_ENCODING) {
    if (interrupt == 1) {
      if (exception_code >= NUM_MACHINE_MODE_INTERRUPT_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      return trap_overrides
          ->machine_mode_interrupt_handler_overrides[exception_code];
    } else {
      if (exception_code >= NUM_MACHINE_MODE_EXCEPTION_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      return trap_overrides
          ->machine_mode_exception_handler_overrides[exception_code];
    }
  } else if (mode == SUPERVISOR_MODE_ENCODING) {
    if (interrupt == 1) {
      if (exception_code >= NUM_SUPERVISOR_MODE_INTERRUPT_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      return trap_overrides
          ->supervisor_mode_interrupt_handler_overrides[exception_code];
    } else {
      if (exception_code >= NUM_SUPERVISOR_MODE_EXCEPTION_HANDLER_OVERRIDES) {
        jumpstart_supervisor_fail();
      }

      return trap_overrides
          ->supervisor_mode_exception_handler_overrides[exception_code];
    }
  }

  jumpstart_supervisor_fail();

  return 0xcafe;
}
