/*
 * SPDX-FileCopyrightText: 2025 Rivos Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include "jumpstart_defines.h"
#include "cpu_bits.h"

.section .jumpstart.cpu.text.mmode.init, "ax"

# Input:
#   a0: hartid
# Output:
#   a0: cpuid
.global convert_hart_id_to_cpu_id
convert_hart_id_to_cpu_id:

  # hart_id = (socket_id << (chiplet_id_size + cluster_id_size + 2)) | \
  #           (chiplet_id << (cluster_id_size + 2)) | (cluster_id << 2) | core_id,
  # Where core_id is 0, 1, 2, or 3
  # Cluster_id: will be hard coded at RTL integration
  # Chiplet-ID: driven from the SDS as DC wires from from the Device_ID_Mapping register (ubump straps - not visible or accessible outside the socket; fuse override option)
  # cluster_id_size: Set to "3" for Gen-1 (recommended from a local HDR in PMD)
  # Socket_Id: driven from the SDS as DC wires from from the Device_ID_Mapping register (ubump straps - visible or accessible outside the socket via GPIO straps; efuse override option)
  # chiplet_id_size: Set to "2" for Gen-1 (recommended from a local HDR in PMD)

  # Cluster ID range: 0
  # Chiplet ID range: 0-1
  # Socket ID range: 0

  # Define sizes for ID fields
  .equ CLUSTER_ID_SIZE, 3
  .equ CHIPLET_ID_SIZE, 2
  .equ CORE_ID_SIZE, 2

  # Extract core_id (bits 0-1) and chiplet_id (bits 5-6)
  # hart_id = (chiplet_id << 5) | core_id
  # logical_id = (chiplet_id * 4) + core_id

  # Save original hart_id
  mv t0, a0

  # Extract core_id (bits 0-1)
  andi t1, t0, ((1 << CORE_ID_SIZE) - 1)  # t1 = core_id (0-3)

  # Extract chiplet_id (bits 5-6)
  srli t2, t0, (CLUSTER_ID_SIZE + CORE_ID_SIZE)  # Shift right to get chiplet_id
  andi t2, t2, ((1 << CHIPLET_ID_SIZE) - 1)      # Mask to get only 2 bits (chiplet_id 0-1)

  # Calculate logical_id = (chiplet_id * 4) + core_id
  slli t3, t2, CORE_ID_SIZE      # t3 = chiplet_id * 4
  add a0, t3, t1                 # a0 = (chiplet_id * 4) + core_id

  ret
