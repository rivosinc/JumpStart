// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

#include <inttypes.h>

void send_ipi_to_supervisor_mode(uint64_t id);

// Triggers `interrupt_id` from the guest interrupt file `guest_id` on hart
// `hart_id`.
void send_interrupt_to_guest(unsigned long hart_id, unsigned long guest_id,
                             uint32_t interrupt_id);

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

void imsic_init(void);
void imsic_fini(void);
