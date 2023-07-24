// SPDX-FileCopyrightText: 2023 Rivos Inc.
//
// SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only

#pragma once

void send_ipi_to_supervisor_mode(uint64_t id)
    __attribute__((section(".jumpstart.text.supervisor")));

void imsic_id_enable(unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));
void imsic_id_disable(unsigned long id)
    __attribute__((section(".jumpstart.text.supervisor")));

void imsic_init(void) __attribute__((section(".jumpstart.text.supervisor")));
void imsic_fini(void) __attribute__((section(".jumpstart.text.supervisor")));
