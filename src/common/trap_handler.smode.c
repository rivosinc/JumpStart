// SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include "cpu_bits.h"
#include "jumpstart.h"

__attr_stext void
register_smode_trap_handler_override(uint64_t mcause,
                                     uint64_t handler_address) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_SMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_smode_fail();
    }

    trap_overrides->smode_interrupt_handler_overrides[exception_code] =
        handler_address;
  } else {
    if (exception_code >= NUM_SMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_smode_fail();
    }

    trap_overrides->smode_exception_handler_overrides[exception_code] =
        handler_address;
  }
}

__attr_stext void deregister_smode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_SMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_smode_fail();
    }

    if (trap_overrides->smode_interrupt_handler_overrides[exception_code] ==
        0x0) {
      jumpstart_smode_fail();
    }

    trap_overrides->smode_interrupt_handler_overrides[exception_code] = 0x0;
  } else {
    if (exception_code >= NUM_SMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_smode_fail();
    }

    if (trap_overrides->smode_exception_handler_overrides[exception_code] ==
        0x0) {
      jumpstart_smode_fail();
    }

    trap_overrides->smode_exception_handler_overrides[exception_code] = 0x0;
  }
}

__attr_stext uint64_t get_smode_trap_handler_override(uint64_t mcause) {
  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_SMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_smode_fail();
    }

    return trap_overrides->smode_interrupt_handler_overrides[exception_code];
  }

  if (exception_code >= NUM_SMODE_EXCEPTION_HANDLER_OVERRIDES) {
    jumpstart_smode_fail();
  }

  return trap_overrides->smode_exception_handler_overrides[exception_code];
}

__attr_stext void
register_vsmode_trap_handler_override(uint64_t mcause,
                                      uint64_t handler_address) {
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_VSMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_vsmode_fail();
    }

    trap_overrides->vsmode_interrupt_handler_overrides[exception_code] =
        handler_address;
  } else {
    if (exception_code >= NUM_VSMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_vsmode_fail();
    }

    trap_overrides->vsmode_exception_handler_overrides[exception_code] =
        handler_address;
  }
}

__attr_stext void deregister_vsmode_trap_handler_override(uint64_t mcause) {
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_VSMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_vsmode_fail();
    }

    if (trap_overrides->vsmode_interrupt_handler_overrides[exception_code] ==
        0x0) {
      jumpstart_vsmode_fail();
    }

    trap_overrides->vsmode_interrupt_handler_overrides[exception_code] = 0x0;
  } else {
    if (exception_code >= NUM_VSMODE_EXCEPTION_HANDLER_OVERRIDES) {
      jumpstart_vsmode_fail();
    }

    if (trap_overrides->vsmode_exception_handler_overrides[exception_code] ==
        0x0) {
      jumpstart_vsmode_fail();
    }

    trap_overrides->vsmode_exception_handler_overrides[exception_code] = 0x0;
  }
}

__attr_stext uint64_t get_vsmode_trap_handler_override(uint64_t mcause) {
  if (get_thread_attributes_current_v_bit_from_smode() != 1) {
    jumpstart_vsmode_fail();
  }

  uint64_t trap_override_struct_address =
      get_thread_attributes_trap_override_struct_address_from_smode();

  struct trap_override_attributes *trap_overrides =
      (struct trap_override_attributes *)trap_override_struct_address;

  uint64_t exception_code = mcause & MCAUSE_EC_MASK;
  uint64_t interrupt = mcause & MCAUSE_INT_FLAG;

  if (interrupt) {
    if (exception_code >= NUM_VSMODE_INTERRUPT_HANDLER_OVERRIDES) {
      jumpstart_vsmode_fail();
    }

    return trap_overrides->vsmode_interrupt_handler_overrides[exception_code];
  }

  if (exception_code >= NUM_VSMODE_EXCEPTION_HANDLER_OVERRIDES) {
    jumpstart_vsmode_fail();
  }

  return trap_overrides->vsmode_exception_handler_overrides[exception_code];
}
