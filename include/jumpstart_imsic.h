// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

void send_ipi_to_supervisor_mode(uint64_t id)
    __attribute__((section(".jumpstart.text.supervisor")));

// Triggers `interrupt_id` from the guest interrupt file `guest_id` on hart `hart_id`.
void send_interrupt_to_guest(unsigned long hart_id,
                             unsigned long guest_id,
                             uint32_t interrupt_id)
    __attribute__((section(".jumpstart.text.supervisor")));


void imsic_id_enable(unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));
void imsic_id_disable(unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));
// Enables the interrupt `id` for the guest interrupt file specified by `guest_id`.
void imsic_id_enable_guest(unsigned guest_id, unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));
// Disables the interrupt `id` for the guest interrupt file specified by `guest_id`.
void imsic_id_disable_guest(unsigned guest_id, unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));

// Enables interrupt delivery and priority for interrupts from guest interrupt file `guest_id`.
void imsic_enable_guest(unsigned guest_id)
    __attribute__((section(".jumpstart.text.supervisor")));
// Disables interrupt delivery and priority for interrupts from guest interrupt file `guest_id`.
void imsic_disable_guest(unsigned guest_id)
    __attribute__((section(".jumpstart.text.supervisor")));

void imsic_init(void) __attribute__((section(".jumpstart.text.supervisor")));
void imsic_fini(void) __attribute__((section(".jumpstart.text.supervisor")));
