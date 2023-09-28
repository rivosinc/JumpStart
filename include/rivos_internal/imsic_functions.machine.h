// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <inttypes.h>

void imsic_machine_init(void);
void imsic_machine_fini(void);

void imsic_machine_id_enable(unsigned long id);
void imsic_machine_id_disable(unsigned long id);
// Triggers `irq` from the machine interrupt file on hart `hart_id`.
void send_interrupt_to_machine_mode(unsigned long hart_id, uint32_t irq);
// Returns the next pending interrupt for the machine mode or 0 if none are
// pending.
uint64_t imsic_next_machine_pending_interrupt(void);

void imsic_machine_update_eithreshold(uint32_t val);
void imsic_machine_update_eidelivery(uint32_t val);
unsigned long imsic_machine_read_eip(unsigned long irq_id);
