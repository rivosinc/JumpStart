/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

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

#define load_reserved_64(addr)                                                 \
  ({                                                                           \
    unsigned long __tmp;                                                       \
    asm volatile("lr.d %0, (%1)" : "=r"(__tmp) : "r"(addr));                   \
    __tmp;                                                                     \
  })

#define store_conditional_64(addr, val)                                        \
  ({                                                                           \
    unsigned long ret = 0;                                                     \
    asm volatile("sc.d %0, %1, (%2)" : "=r"(ret) : "r"(val), "r"(addr));       \
    ret;                                                                       \
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
int run_function_in_vsmode(uint64_t function_address, ...);
int run_function_in_vumode(uint64_t function_address, ...);

void setup_mmu_from_smode(void);
void disable_mmu_from_smode(void);

uint64_t get_mmode_trap_handler_override(uint64_t mcause);
void register_mmode_trap_handler_override(uint64_t mcause,
                                          uint64_t handler_address);
void deregister_mmode_trap_handler_override(uint64_t mcause);

uint64_t get_smode_trap_handler_override(uint64_t scause);
void register_smode_trap_handler_override(uint64_t scause,
                                          uint64_t handler_address);
void deregister_smode_trap_handler_override(uint64_t scause);

uint64_t get_vsmode_trap_handler_override(uint64_t vscause);
void register_vsmode_trap_handler_override(uint64_t vscause,
                                           uint64_t handler_address);
void deregister_vsmode_trap_handler_override(uint64_t vscause);

uint64_t get_thread_attributes_bookend_magic_number_from_smode(void);
uint64_t get_thread_attributes_trap_override_struct_address_from_smode(void);
uint8_t get_thread_attributes_current_mode_from_smode(void);
uint8_t get_thread_attributes_current_v_bit_from_smode(void);
uint8_t get_thread_attributes_cpu_id_from_smode(void);
uint8_t get_thread_attributes_physical_cpu_id_from_smode(void);
uint64_t get_thread_attributes_marchid_from_smode(void);
uint64_t get_thread_attributes_mimpid_from_smode(void);
uint8_t get_thread_attributes_vsmode_setup_done_from_smode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_smode_from_smode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_smode_from_mmode(void);

struct thread_attributes *
get_thread_attributes_for_cpu_id_from_smode(uint8_t cpu_id);

uint8_t get_physical_cpu_id_for_cpu_id_from_smode(uint8_t cpu_id);

struct thread_attributes *
get_thread_attributes_for_cpu_id_from_mmode(uint8_t cpu_id);

uint8_t get_physical_cpu_id_for_cpu_id_from_mmode(uint8_t cpu_id);

uint64_t get_thread_attributes_bookend_magic_number_from_mmode(void);
uint64_t get_thread_attributes_trap_override_struct_address_from_mmode(void);
uint8_t get_thread_attributes_current_mode_from_mmode(void);
uint8_t get_thread_attributes_current_v_bit_from_mmode(void);
uint8_t get_thread_attributes_cpu_id_from_mmode(void);
uint8_t get_thread_attributes_physical_cpu_id_from_mmode(void);
uint64_t get_thread_attributes_marchid_from_mmode(void);
uint64_t get_thread_attributes_mimpid_from_mmode(void);
uint8_t get_thread_attributes_smode_setup_done_from_mmode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_mmode_from_mmode(void);
uint8_t
get_thread_attributes_num_context_saves_remaining_in_mmode_from_smode(void);

void sync_all_cpus_from_smode(void);
void sync_all_cpus_from_mmode(void);
void sync_cpus_in_mask_from_smode(uint64_t cpu_mask,
                                  uint64_t sync_point_address);
void sync_cpus_in_mask_from_mmode(uint64_t cpu_mask,
                                  uint64_t sync_point_address);

void jumpstart_umode_fail(void) __attribute__((noreturn));
void jumpstart_smode_fail(void) __attribute__((noreturn));
void jumpstart_vsmode_fail(void) __attribute__((noreturn));
void jumpstart_vumode_fail(void) __attribute__((noreturn));
void jumpstart_mmode_fail(void) __attribute__((noreturn));

uint64_t get_mepc_for_current_exception(void);
void set_mepc_for_current_exception(uint64_t new_mepc);

uint64_t get_sepc_for_current_exception(void);
void set_sepc_for_current_exception(uint64_t new_sepc);

void exit_from_smode(uint64_t return_code) __attribute__((noreturn));

#define __attr_stext __attribute__((section(".jumpstart.cpu.text.smode")))
#define __attr_privdata                                                        \
  __attribute__((section(".jumpstart.cpu.data.privileged")))

// Only functions that need to be placed in the 4K mmode init section
// should be marked with __attr_mtext_init.
#define __attr_mtext_init                                                      \
  __attribute__((section(".jumpstart.cpu.text.mmode.init")))
#define __attr_mtext __attribute__((section(".jumpstart.cpu.text.mmode")))

__attr_stext uint64_t read_time(void);
