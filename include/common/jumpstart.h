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
    __asm__ __volatile__("csrrw %0, " __ASM_STR(reg) ", %1"                    \
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

#define STRINGIFY(x)  #x
#define ADD_QUOTES(x) STRINGIFY(x)
// Disables instruction by instruction checking when running on the simulator,
#define disable_checktc()                                                      \
  __asm__ __volatile__(ADD_QUOTES(CHECKTC_DISABLE)::: "memory")
// Enables instruction by instruction checking when running on the simulator,
#define enable_checktc()                                                       \
  __asm__ __volatile__(ADD_QUOTES(CHECKTC_ENABLE)::: "memory")

// The functions run through the run_function_in_*mode() functions can be
// passed up to 6 arguments.
int run_function_in_umode(uint64_t function_address, ...);
int run_function_in_smode(uint64_t function_address, ...);

void disable_mmu_from_smode(void);

uint64_t get_mmode_trap_handler_override(uint64_t mcause);
void register_mmode_trap_handler_override(uint64_t mcause,
                                          uint64_t handler_address);
void deregister_mmode_trap_handler_override(uint64_t mcause);

uint64_t get_smode_trap_handler_override(uint64_t mcause);
void register_smode_trap_handler_override(uint64_t mcause,
                                          uint64_t handler_address);
void deregister_smode_trap_handler_override(uint64_t mcause);

uint64_t get_thread_attributes_bookend_magic_number_from_smode(void);
uint64_t get_thread_attributes_trap_override_struct_address_from_smode(void);
uint8_t get_thread_attributes_current_mode_from_smode(void);
uint8_t get_thread_attributes_hart_id_from_smode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_smode_from_smode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_smode_from_mmode(void);

uint64_t get_thread_attributes_bookend_magic_number_from_mmode(void);
uint64_t get_thread_attributes_trap_override_struct_address_from_mmode(void);
uint8_t get_thread_attributes_current_mode_from_mmode(void);
uint8_t get_thread_attributes_hart_id_from_mmode(void);
uint8_t get_thread_attributes_smode_setup_done_from_mmode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_mmode_from_smode(void);

uint8_t get_diag_satp_mode_from_smode(void);

uint64_t get_active_hart_mask_from_smode(void);
uint64_t get_active_hart_mask_from_mmode(void);

void sync_all_harts_from_smode(void);
void sync_all_harts_from_mmode(void);

void jumpstart_umode_fail(void) __attribute__((noreturn));
void jumpstart_smode_fail(void) __attribute__((noreturn));
void jumpstart_mmode_fail(void) __attribute__((noreturn));

uint64_t get_mepc_for_current_exception(void);
void set_mepc_for_current_exception(uint64_t new_mepc);

uint64_t get_sepc_for_current_exception(void);
void set_sepc_for_current_exception(uint64_t new_sepc);

#define __attr_stext __attribute__((section(".jumpstart.text.smode")))
#define __attr_mtext __attribute__((section(".jumpstart.text.mmode")))
