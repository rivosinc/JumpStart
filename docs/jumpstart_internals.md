<!--
SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.

SPDX-License-Identifier: Apache-2.0
-->

# JumpStart Internals

## End of Simulation

The `run_end_of_sim_sequence()` assembly function is called at the end of the simulation. It contains code to cause the simulator to terminate running the diag and exit with the PASS/FAIL status as it's error code.

This function can be updated to add support for additional simulators.
