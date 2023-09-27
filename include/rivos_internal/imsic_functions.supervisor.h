// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <inttypes.h>

void imsic_init(void);
void imsic_fini(void);

void imsic_id_enable(unsigned long id);
void imsic_id_disable(unsigned long id);
// Enables the interrupt `id` for the guest interrupt file specified by
// `guest_id`.
void imsic_id_enable_guest(unsigned guest_id, unsigned long id);
// Disables the interrupt `id` for the guest interrupt file specified by
// `guest_id`.
void imsic_id_disable_guest(unsigned guest_id, unsigned long id);

// Enables interrupt delivery and priority for interrupts from guest interrupt
// file `guest_id`.
void imsic_enable_guest(unsigned guest_id);
// Disables interrupt delivery and priority for interrupts from guest interrupt
// file `guest_id`.
void imsic_disable_guest(unsigned guest_id);

// Triggers `irq` from the supervisor interrupt file on hart `hart_id`.
void send_interrupt_to_supervisor_mode(unsigned long hart_id, uint32_t irq);
// Returns the next pending interrupt for the supervisor mode or 0 if none are
// pending.
uint64_t imsic_next_supervisor_pending_interrupt(void);

// Triggers `interrupt_id` from the guest interrupt file `guest_id` on hart
// `hart_id`.
void send_interrupt_to_guest(unsigned long hart_id, unsigned long guest_id,
                             uint32_t interrupt_id);
// Returns the next pending interrupt for the guest interrupt file `guest_id` or
// 0 if none are pending.
uint64_t imsic_next_guest_pending_interrupt(unsigned guest_id);

void imsic_update_eithreshold(uint32_t val);
void imsic_update_eidelivery(uint32_t val);
unsigned long imsic_read_eip(unsigned long irq_id);
