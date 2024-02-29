# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

#define SBI_HSM_EID               0x48534D
#define SBI_HSM_HART_START_FID    0
#define SBI_HSM_HART_STOP_FID     1
#define SBI_HSM_HART_STATUS_FID   2
#define SBI_SRST_EID              0x53525354
#define SBI_SRST_SYSTEM_RESET_FID 0

.section .jumpstart.text.smode, "ax"

# Reference:
# https://github.com/riscv-non-isa/riscv-sbi-doc/blob/master/src/ext-hsm.adoc

# Prototype:
# struct sbiret sbi_hart_start(unsigned long hartid,
#                              unsigned long start_addr,
#                              unsigned long opaque)
.global sbi_hart_start
sbi_hart_start:
  li a6, SBI_HSM_HART_START_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_hart_stop(void)
.global sbi_hart_stop
sbi_hart_stop:
  li a6, SBI_HSM_HART_STOP_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_hart_get_status(unsigned long hartid)
.global sbi_hart_get_status
sbi_hart_get_status:
  li a6, SBI_HSM_HART_STATUS_FID
  li a7, SBI_HSM_EID
  ecall
  ret

# Prototype:
# struct sbiret sbi_system_reset(uint32_t reset_type, uint32_t reset_reason)
.global sbi_system_reset
sbi_system_reset:
  li a6, SBI_SRST_SYSTEM_RESET_FID
  li a7, SBI_SRST_EID
  ecall
  ret
