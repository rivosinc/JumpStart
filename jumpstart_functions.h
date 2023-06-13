// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

#include <inttypes.h>

#include "jumpstart_data_structures.h"
#include "jumpstart_defines.h"

void jump_to_user_mode(void) __attribute__((section(".jumpstart.text")));
void jump_to_supervisor_mode(void) __attribute__((section(".jumpstart.text")));

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

uint64_t get_diag_satp_ppn(void) __attribute__((section(".jumpstart.text")));
uint8_t get_diag_satp_mode(void) __attribute__((section(".jumpstart.text")));

void jumpstart_fail(void) __attribute__((section(".jumpstart.text")));
