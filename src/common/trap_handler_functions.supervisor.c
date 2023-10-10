// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart_functions.h"

__attribute__((section(".jumpstart.text.supervisor"))) void
register_supervisor_mode_trap_handler_override(uint64_t mcause,
                                               uint64_t handler_address) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_supervisor_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
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
}

__attribute__((section(".jumpstart.text.supervisor"))) uint64_t
get_supervisor_mode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_supervisor_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
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

  jumpstart_supervisor_fail();
}

__attribute__((section(".jumpstart.text.machine"))) void
register_machine_mode_trap_handler_override(uint64_t mcause,
                                            uint64_t handler_address) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_machine_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_MACHINE_MODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_machine_fail();
    }

    trap_overrides->machine_mode_interrupt_handler_overrides[exception_code] =
        handler_address;
  } else {
    if (exception_code >= NUM_MACHINE_MODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_machine_fail();
    }

    trap_overrides->machine_mode_exception_handler_overrides[exception_code] =
        handler_address;
  }
}

__attribute__((section(".jumpstart.text.machine"))) uint64_t
get_machine_mode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_machine_mode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_MACHINE_MODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_machine_fail();
    }

    return trap_overrides
        ->machine_mode_interrupt_handler_overrides[exception_code];
  } else {
    if (exception_code >= NUM_MACHINE_MODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_machine_fail();
    }

    return trap_overrides
        ->machine_mode_exception_handler_overrides[exception_code];
  }

  jumpstart_machine_fail();
}
