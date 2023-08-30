// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

#include <inttypes.h>

#include "jumpstart_data_structures.h"
#include "jumpstart_defines.h"

#define read_csr(reg)                                                          \
  ({                                                                           \
    unsigned long __tmp;                                                       \
    asm volatile("csrr %0, " #reg : "=r"(__tmp));                              \
    __tmp;                                                                     \
  })

#define write_csr(reg, val) ({ asm volatile("csrw " #reg ", %0" ::"rK"(val)); })

#define set_csr(reg, val)   ({ asm volatile("csrs " #reg ", %0" ::"rK"(val)); })
#define clear_csr(reg, val) ({ asm volatile("csrc " #reg ", %0" ::"rK"(val)); })

#define read_set_csr(reg, val)                                                 \
  ({                                                                           \
    unsigned long __v = (unsigned long)(val);                                  \
    __asm__ __volatile__("csrrs %0, " #reg ", %1"                              \
                         : "=r"(__v)                                           \
                         : "rK"(__v)                                           \
                         : "memory");                                          \
    __v;                                                                       \
  })

#define read_clear_csr(reg, val)                                               \
  ({                                                                           \
    unsigned long __v = (unsigned long)(val);                                  \
    __asm__ __volatile__("csrrc %0, " #reg ", %1"                              \
                         : "=r"(__v)                                           \
                         : "rK"(__v)                                           \
                         : "memory");                                          \
    __v;                                                                       \
  })

int run_function_in_user_mode(uint64_t function_address);
int run_function_in_supervisor_mode(uint64_t function_address);

void disable_mmu_from_supervisor_mode(void);

uint64_t get_machine_mode_trap_handler_override(uint64_t mcause);
void register_machine_mode_trap_handler_override(uint64_t mcause,
                                                 uint64_t handler_address);

uint64_t get_supervisor_mode_trap_handler_override(uint64_t mcause);
void register_supervisor_mode_trap_handler_override(uint64_t mcause,
                                                    uint64_t handler_address);

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

void jumpstart_supervisor_fail(void) __attribute__((noreturn));
void jumpstart_fail(void) __attribute__((noreturn));
