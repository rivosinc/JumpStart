<!--
SPDX-FileCopyrightText: 2023 Rivos Inc.

SPDX-License-Identifier: LicenseRef-Rivos-Internal-Only
-->

# JumpStart

Firmware framework for CPU validation. Provides kernel and APIs for users to
run directed tests.

## Build and Test

This will build `jumptest` and run it on Spike.

```
meson setup builddir --cross-file cross-file.txt --buildtype release
meson compile -C builddir
meson test -C builddir
```
