# SPDX-FileCopyrightText: 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import subprocess
from typing import Optional


def get_elf_entry_point(elf_path: str) -> Optional[str]:
    """
    Return the ELF entry point address as a hex string prefixed with 0x (e.g. "0x90000000").
    Uses riscv64-unknown-elf-readelf to extract the value.
    """
    try:
        result = subprocess.run(
            ["riscv64-unknown-elf-readelf", "-h", elf_path], capture_output=True, text=True
        )
        if result.returncode != 0:
            log.error(f"readelf failed for {elf_path}: {result.stderr}")
            return None
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if line.lower().startswith("entry point address:"):
                # Expected formats:
                #   Entry point address: 0x90000000
                #   Entry point address: 0x0000000090000000
                try:
                    value = line.split(":", 1)[1].strip()
                except Exception:
                    value = ""
                if not value:
                    return None
                value = value.lower()
                if value.startswith("0x"):
                    return value
                # Fallback if readelf ever returns a plain number
                return f"0x{value}"
    except Exception as exc:
        log.error(f"Failed to read ELF entry point from {elf_path}: {exc}")
    return None
