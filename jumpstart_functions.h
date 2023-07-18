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

void setup_mmu_for_supervisor_mode(void)
    __attribute__((section(".jumpstart.text")));
void disable_mmu_for_supervisor_mode(void)
    __attribute__((section(".jumpstart.text")));

uint64_t get_trap_handler_override(uint64_t mcause)
    __attribute__((section(".jumpstart.text")));
void register_trap_handler_override(uint8_t mode, uint64_t mcause,
                                    uint64_t handler_address)
    __attribute__((section(".jumpstart.text")));

uint64_t get_thread_attributes_bookend_magic_number(void)
    __attribute__((section(".jumpstart.text")));
uint64_t get_thread_attributes_trap_override_struct_address(void)
    __attribute__((section(".jumpstart.text")));
uint8_t get_thread_attributes_current_mode(void)
    __attribute__((section(".jumpstart.text")));
uint8_t get_thread_attributes_hart_id(void)
    __attribute__((section(".jumpstart.text")));

uint64_t get_thread_attributes_bookend_magic_number_in_machine_mode(void)
    __attribute__((section(".jumpstart.text.machine")));
uint64_t
get_thread_attributes_trap_override_struct_address_in_machine_mode(void)
    __attribute__((section(".jumpstart.text.machine")));
uint8_t get_thread_attributes_current_mode_in_machine_mode(void)
    __attribute__((section(".jumpstart.text.machine")));
uint8_t get_thread_attributes_hart_id_in_machine_mode(void)
    __attribute__((section(".jumpstart.text.machine")));

uint64_t get_diag_satp_ppn(void) __attribute__((section(".jumpstart.text")));
uint8_t get_diag_satp_mode(void) __attribute__((section(".jumpstart.text")));

void jumpstart_supervisor_fail(void)
    __attribute__((section(".jumpstart.text")));
