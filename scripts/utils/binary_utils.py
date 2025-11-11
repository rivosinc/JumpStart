# SPDX-FileCopyrightText: 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import subprocess
from pathlib import Path
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


def generate_padded_binary_from_elf(
    elf_path: str, output_dir_path: Optional[str] = None, name_for_logs: Optional[str] = None
) -> Optional[str]:
    """
    Generate a .bin file from an ELF file using objcopy and truncate commands,
    then return the path to the generated binary (or None on failure).

    Args:
        elf_path: Path to the ELF file
        output_dir_path: Optional directory path where the padded .bin should be written. If not
            provided, the binary will be created next to the ELF.
        name_for_logs: Optional friendly name used in log messages
    """
    try:
        elf_path_p = Path(elf_path)
        if not elf_path_p.exists():
            log.error(f"ELF path does not exist: {elf_path}")
            return None

        # Determine output directory and filename
        entry = get_elf_entry_point(str(elf_path_p))
        entry_suffix = entry if entry else "0x0"
        out_dir_p = Path(output_dir_path) if output_dir_path else elf_path_p.parent
        bin_filename = f"{elf_path_p.stem}.{entry_suffix}.padded.bin"
        bin_path_p = out_dir_p / bin_filename
        out_dir_p.mkdir(parents=True, exist_ok=True)

        display_name = name_for_logs or elf_path_p.name

        objcopy_cmd = [
            "riscv64-unknown-elf-objcopy",
            "-O",
            "binary",
            str(elf_path_p),
            str(bin_path_p),
        ]
        log.debug(f"Generating .padded.bin file for {display_name} with: {' '.join(objcopy_cmd)}")
        result = subprocess.run(objcopy_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(f"objcopy failed for {display_name}: {result.stderr}")
            return None

        truncate_cmd = ["truncate", "-s", "%4", str(bin_path_p)]
        log.debug(
            f"Truncating .padded.bin to 4-byte boundary for {display_name}: {' '.join(truncate_cmd)}"
        )
        result = subprocess.run(truncate_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.error(f"truncate failed for {display_name}: {result.stderr}")
            return None

        return str(bin_path_p)
    except Exception as exc:
        log.error(f"Failed to generate padded binary from ELF {elf_path}: {exc}")
        return None
