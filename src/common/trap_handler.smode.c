/*
 * SPDX-FileCopyrightText: 2025 - 2026 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "cpu_bits.h"
#include "jumpstart.h"
#include "uart.smode.h"

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

// Helper function to get exception name
__attr_stext static const char *get_exception_name(uint64_t exception_id) {
  switch (exception_id) {
  case RISCV_EXCP_INST_ADDR_MIS:
    return "Instruction Address Misaligned";
  case RISCV_EXCP_INST_ACCESS_FAULT:
    return "Instruction Access Fault";
  case RISCV_EXCP_ILLEGAL_INST:
    return "Illegal Instruction";
  case RISCV_EXCP_BREAKPOINT:
    return "Breakpoint";
  case RISCV_EXCP_LOAD_ADDR_MIS:
    return "Load Address Misaligned";
  case RISCV_EXCP_LOAD_ACCESS_FAULT:
    return "Load Access Fault";
  case RISCV_EXCP_STORE_AMO_ADDR_MIS:
    return "Store/AMO Address Misaligned";
  case RISCV_EXCP_STORE_AMO_ACCESS_FAULT:
    return "Store/AMO Access Fault";
  case RISCV_EXCP_U_ECALL:
    return "User ECALL";
  case RISCV_EXCP_S_ECALL:
    return "Supervisor ECALL";
  case RISCV_EXCP_VS_ECALL:
    return "Virtual Supervisor ECALL";
  case RISCV_EXCP_M_ECALL:
    return "Machine ECALL";
  case RISCV_EXCP_INST_PAGE_FAULT:
    return "Instruction Page Fault";
  case RISCV_EXCP_LOAD_PAGE_FAULT:
    return "Load Page Fault";
  case RISCV_EXCP_STORE_PAGE_FAULT:
    return "Store Page Fault";
  case RISCV_EXCP_SW_CHECK:
    return "SW check";
  case RISCV_EXCP_HW_ERR:
    return "HW Error";
  default:
    return "Unknown Exception";
  }
}

// Default exception handler for unexpected exceptions
__attr_stext void default_smode_exception_handler(void) {
  uint8_t cpu_id = get_thread_attributes_cpu_id_from_smode();
  uint64_t exception_id = read_csr(scause) & SCAUSE_EC_MASK;
  uint64_t sepc = read_csr(sepc);
  uint64_t stval = read_csr(stval);
  uint64_t sstatus = read_csr(sstatus);

  printk("CPU_%d_LOG: ERROR: Unexpected exception occurred!\n", cpu_id);
  printk("CPU_%d_LOG: Exception details:\n", cpu_id);
  printk("CPU_%d_LOG: Exception ID: 0x%lx (%s)\n", cpu_id, exception_id,
         get_exception_name(exception_id));
  printk("CPU_%d_LOG: Program Counter (sepc): 0x%lx\n", cpu_id, sepc);
  printk("CPU_%d_LOG: Trap Value (stval): 0x%lx\n", cpu_id, stval);
  printk("CPU_%d_LOG: Status Register (sstatus): 0x%lx\n", cpu_id, sstatus);
  printk(
      "CPU_%d_LOG: Status bits: SPP=%d | SIE=%d | SPIE=%d | UBE=%d | SBE=%d\n",
      cpu_id,
      (int)((sstatus >> SSTATUS_SPP_POS) & 1), // SPP - Previous privilege level
      (int)((sstatus >> SSTATUS_SIE_POS) &
            1), // SIE - Supervisor Interrupt Enable
      (int)((sstatus >> SSTATUS_SPIE_POS) &
            1), // SPIE - Previous Interrupt Enable
      (int)((sstatus >> SSTATUS_UBE_POS) & 1), // UBE - User mode endianness
      (int)((sstatus >> SSTATUS_SBE_POS) &
            1)); // SBE - Supervisor mode endianness

  jumpstart_smode_fail();
}

// Register handlers for all exceptions except the ecalls.
// The ecalls are expected as we use them to move between modes.
__attr_stext void register_default_smode_exception_handlers(void) {
  register_smode_trap_handler_override(
      RISCV_EXCP_INST_ADDR_MIS, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_INST_ACCESS_FAULT,
      (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_ILLEGAL_INST, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_BREAKPOINT, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_LOAD_ADDR_MIS, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_LOAD_ACCESS_FAULT,
      (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_STORE_AMO_ADDR_MIS,
      (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_STORE_AMO_ACCESS_FAULT,
      (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_INST_PAGE_FAULT, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_LOAD_PAGE_FAULT, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_STORE_PAGE_FAULT,
      (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_SW_CHECK, (uint64_t)(&default_smode_exception_handler));
  register_smode_trap_handler_override(
      RISCV_EXCP_HW_ERR, (uint64_t)(&default_smode_exception_handler));
}
