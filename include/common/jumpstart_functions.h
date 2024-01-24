// SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <inttypes.h>
#include <stdarg.h>

#include "jumpstart_data_structures.h"
#include "jumpstart_defines.h"

#define __ASM_STR(x)  #x

#define ARRAY_SIZE(a) (sizeof(a) / sizeof(*a))

#define read_csr(reg)                                                          \
  ({                                                                           \
    unsigned long __tmp;                                                       \
    asm volatile("csrr %0, " __ASM_STR(reg) : "=r"(__tmp));                    \
    __tmp;                                                                     \
  })

#define write_csr(reg, val)                                                    \
  ({ asm volatile("csrw " __ASM_STR(reg) ", %0" ::"rK"(val)); })

#define read_write_csr(reg, val)                                               \
  ({                                                                           \
    unsigned long __v = (unsigned long)(val);                                  \
    __asm__ __volatile__("csrrw %0, " #reg ", %1"                              \
                         : "=r"(__v)                                           \
                         : "rK"(__v)                                           \
                         : "memory");                                          \
    __v;                                                                       \
  })

#define set_csr(reg, val)                                                      \
  ({ asm volatile("csrs " __ASM_STR(reg) ", %0" ::"rK"(val)); })
#define clear_csr(reg, val)                                                    \
  ({ asm volatile("csrc " __ASM_STR(reg) ", %0" ::"rK"(val)); })

#define read_set_csr(reg, val)                                                 \
  ({                                                                           \
    unsigned long __v = (unsigned long)(val);                                  \
    __asm__ __volatile__("csrrs %0, " __ASM_STR(reg) ", %1"                    \
                         : "=r"(__v)                                           \
                         : "rK"(__v)                                           \
                         : "memory");                                          \
    __v;                                                                       \
  })

#define read_clear_csr(reg, val)                                               \
  ({                                                                           \
    unsigned long __v = (unsigned long)(val);                                  \
    __asm__ __volatile__("csrrc %0, " __ASM_STR(reg) ", %1"                    \
                         : "=r"(__v)                                           \
                         : "rK"(__v)                                           \
                         : "memory");                                          \
    __v;                                                                       \
  })

#define STRINGIFY(x)      #x
#define ADD_QUOTES(x)     STRINGIFY(x)
// Disables instruction by instruction checking when running on the simulator,
#define disable_checktc() __asm__ __volatile__(ADD_QUOTES(CHECKTC_DISABLE))
// Enables instruction by instruction checking when running on the simulator,
#define enable_checktc()  __asm__ __volatile__(ADD_QUOTES(CHECKTC_ENABLE))

// The functions run through the run_function_in_*mode() functions can be
// passed up to 6 arguments.
int run_function_in_umode(uint64_t function_address, ...);
int run_function_in_smode(uint64_t function_address, ...);

void disable_mmu_from_supervisor_mode(void);

uint64_t get_machine_mode_trap_handler_override(uint64_t mcause);
void register_machine_mode_trap_handler_override(uint64_t mcause,
                                                 uint64_t handler_address);
void deregister_machine_mode_trap_handler_override(uint64_t mcause);

uint64_t get_supervisor_mode_trap_handler_override(uint64_t mcause);
void register_supervisor_mode_trap_handler_override(uint64_t mcause,
                                                    uint64_t handler_address);
void deregister_supervisor_mode_trap_handler_override(uint64_t mcause);

uint64_t get_thread_attributes_bookend_magic_number_from_supervisor_mode(void);
uint64_t
get_thread_attributes_trap_override_struct_address_from_supervisor_mode(void);
uint8_t get_thread_attributes_current_mode_from_supervisor_mode(void);
uint8_t get_thread_attributes_hart_id_from_supervisor_mode(void);

uint64_t get_thread_attributes_bookend_magic_number_from_machine_mode(void);
uint64_t
get_thread_attributes_trap_override_struct_address_from_machine_mode(void);
uint8_t get_thread_attributes_current_mode_from_machine_mode(void);
uint8_t get_thread_attributes_hart_id_from_machine_mode(void);

uint8_t get_diag_satp_mode_from_supervisor_mode(void);

uint64_t get_active_hart_mask_from_supervisor_mode(void);
uint64_t get_active_hart_mask_from_machine_mode(void);

void sync_all_harts_from_supervisor_mode(void);
void sync_all_harts_from_machine_mode(void);

void jumpstart_umode_fail(void) __attribute__((noreturn));
void jumpstart_supervisor_fail(void) __attribute__((noreturn));
void jumpstart_machine_fail(void) __attribute__((noreturn));
