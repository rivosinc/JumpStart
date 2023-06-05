// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

#include <inttypes.h>

#include "jumpstart_data_structures.h"
#include "jumpstart_defines.h"

void jump_to_user_mode(void);
void jump_to_supervisor_mode(void);

void setup_mmu_for_supervisor_mode(void);
void disable_mmu_for_supervisor_mode(void);

uint64_t get_trap_handler_override(uint64_t mcause);
void register_trap_handler_override(uint8_t mode, uint64_t mcause,
                                    uint64_t handler_address);

uint64_t get_thread_bookend_magic_number(void);
uint64_t get_thread_trap_override_struct_address(void);
uint8_t get_thread_current_mode(void);
uint8_t get_thread_hart_id(void);

uint64_t get_diag_satp_ppn(void);
uint8_t get_diag_satp_mode(void);

void jumpstart_fail(void);
