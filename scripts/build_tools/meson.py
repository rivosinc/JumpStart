# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging as log
import os
import pprint
import subprocess
import sys
from typing import Any, Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from data_structures import DictUtils  # noqa
from system import functions as system_functions  # noqa


class MesonBuildError(Exception):
    """Custom exception for Meson build failures."""

    def __init__(self, message, return_code=1):
        self.message = message
        self.return_code = return_code
        super().__init__(self.message)


def quote_if_needed(x):
    x_str = str(x)
    if (x_str.startswith("'") and x_str.endswith("'")) or (
        x_str.startswith('"') and x_str.endswith('"')
    ):
        return x_str
    return f"'{x_str}'"


class Meson:
    supported_toolchains: List[str] = ["gcc", "llvm", "gcc15"]

    def __init__(
        self,
        toolchain: str,
        jumpstart_dir: str,
        diag_name: str,
        diag_sources: List[str],
        diag_attributes_yaml: str,
        builddir: str,
    ) -> None:
        self.meson_builddir = None

        assert toolchain in self.supported_toolchains
        self.toolchain = toolchain

        if not os.path.exists(jumpstart_dir):
            raise Exception(f"Jumpstart directory does not exist: {jumpstart_dir}")
        self.jumpstart_dir = os.path.abspath(jumpstart_dir)

        self.diag_name = diag_name

        self.meson_options: Dict[str, Any] = {}

        # Ensure build directory exists and is absolute
        if not os.path.isabs(builddir):
            builddir = os.path.abspath(builddir)
        if not os.path.exists(builddir):
            raise Exception(f"Meson build directory does not exist: {builddir}")
        self.meson_builddir = builddir

        self.setup_default_meson_options(
            diag_sources,
            diag_attributes_yaml,
        )

    def setup_default_meson_options(
        self,
        diag_sources: List[str],
        diag_attributes_yaml: str,
    ) -> None:
        self.meson_options["diag_name"] = self.diag_name
        self.meson_options["diag_sources"] = diag_sources
        self.meson_options["diag_attributes_yaml"] = diag_attributes_yaml
        self.meson_options["diag_attribute_overrides"] = []

        # Default buildtype. Can be overridden by YAML or CLI meson option overrides.
        self.meson_options["buildtype"] = "release"

        self.meson_options["spike_additional_arguments"] = []
        self.meson_options["qemu_additional_arguments"] = []

        self.trace_file = f"{self.meson_builddir}/{self.diag_name}.itrace"

        # Override rig_path option if the RIG_ROOT env variable is set from loading the
        # rivos-sdk/rig module our sourcing rig_env.sh.
        if os.getenv("RIG_ROOT") is not None:
            self.meson_options["rig_path"] = os.getenv("RIG_ROOT")

    def override_meson_options_from_dict(self, overrides_dict: Dict[str, Any]) -> None:
        if overrides_dict is None:
            return
        DictUtils.override_dict(self.meson_options, overrides_dict, False, True)

    def get_meson_options(self) -> Dict[str, Any]:
        """Return the current Meson options as a dict."""
        return self.meson_options

    def get_meson_options_pretty(self, width: int = 120, spacing: str = "") -> str:
        """Return a pretty-printed string of the Meson options.

        spacing: A prefix added to each line to control left padding in callers.
        """
        formatted = pprint.pformat(self.meson_options, width=width)
        if spacing:
            return "\n".join(f"{spacing}{line}" for line in formatted.splitlines())
        return formatted

    def setup(self):
        self.meson_setup_flags = {}
        for option in self.meson_options:
            if isinstance(self.meson_options[option], list):
                if len(self.meson_options[option]) == 0:
                    continue
                self.meson_setup_flags[f"-D{option}"] = (
                    "[" + ",".join(quote_if_needed(x) for x in self.meson_options[option]) + "]"
                )
            elif isinstance(self.meson_options[option], bool):
                self.meson_setup_flags[f"-D{option}"] = str(self.meson_options[option]).lower()
            else:
                self.meson_setup_flags[f"-D{option}"] = self.meson_options[option]

        meson_setup_command = ["meson", "setup", self.meson_builddir]
        for flag in self.meson_setup_flags:
            meson_setup_command.append(f"{flag}={self.meson_setup_flags[flag]}")

        meson_setup_command.extend(
            [
                "--cross-file",
                os.path.join(
                    self.jumpstart_dir, f"cross_compile/public/{self.toolchain}_options.txt"
                ),
                "--cross-file",
                os.path.join(self.jumpstart_dir, f"cross_compile/{self.toolchain}.txt"),
            ]
        )

        log.debug("Meson options:\n%s", self.get_meson_options_pretty(spacing="\t"))

        # Print the meson setup command in a format that can be copy-pasted to
        # reproduce the build.
        printable_meson_setup_command = " ".join(meson_setup_command)
        printable_meson_setup_command = printable_meson_setup_command.replace("'", "\\'")
        log.debug(f"meson setup: {self.diag_name}")
        log.debug(printable_meson_setup_command)
        return_code = system_functions.run_command(meson_setup_command, self.jumpstart_dir)
        if return_code != 0:
            error_msg = f"meson setup failed. Check: {self.meson_builddir}"
            log.error(error_msg)
            raise MesonBuildError(error_msg, return_code)

    def compile(self):
        meson_compile_command = ["meson", "compile", "-v", "-C", self.meson_builddir]
        log.debug(f"meson compile: {self.diag_name}")
        log.debug(" ".join(meson_compile_command))
        return_code = system_functions.run_command(meson_compile_command, self.jumpstart_dir)

        diag_elf = os.path.join(self.meson_builddir, self.diag_name + ".elf")
        diag_disasm = os.path.join(self.meson_builddir, self.diag_name + ".dis")

        if return_code == 0:
            if not os.path.exists(diag_elf):
                error_msg = f"diag elf not created by meson compile. Check: {self.meson_builddir}"
                raise MesonBuildError(error_msg)

        if return_code != 0:
            error_msg = f"Compile failed. Check: {self.meson_builddir}"
            log.error(error_msg)
            raise MesonBuildError(error_msg, return_code)

        compiled_assets = {}
        if os.path.exists(diag_disasm):
            compiled_assets["disasm"] = diag_disasm
        if os.path.exists(diag_elf):
            compiled_assets["elf"] = diag_elf
        return compiled_assets

    def test(self):
        meson_test_command = ["meson", "test", "-v", "-C", self.meson_builddir]
        log.debug(f"meson test: {self.diag_name}")
        log.debug(" ".join(meson_test_command))
        return_code = system_functions.run_command(meson_test_command, self.jumpstart_dir)

        run_assets = {}

        generate_trace = bool(self.meson_options.get("generate_trace", False))
        if generate_trace:
            if return_code == 0 and not os.path.exists(self.trace_file):
                error_msg = f"Run passed but trace file not created. Check: {self.meson_builddir}"
                raise MesonBuildError(error_msg)

            run_assets["trace"] = self.trace_file
        elif self.trace_file and os.path.exists(self.trace_file):
            error_msg = f"Trace generation was disabled but trace file {self.trace_file} created. Check: {self.meson_builddir}"
            raise MesonBuildError(error_msg)

        if return_code != 0:
            error_msg = f"Run failed. Check: {self.meson_builddir}"
            log.error(error_msg)
            raise MesonBuildError(error_msg, return_code)

        return run_assets

    def introspect(self):
        """Run meson introspect and store the build options."""
        # --- Run meson introspect and store build options ---

        # Use subprocess.run to run the introspect command and capture output
        introspect_cmd = ["meson", "introspect", self.meson_builddir, "--buildoptions"]
        log.debug(f"Running meson introspect: {' '.join(introspect_cmd)}")
        try:
            result = subprocess.run(
                introspect_cmd,
                cwd=self.jumpstart_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            result_code = result.returncode
            result_out = result.stdout
        except Exception as e:
            log.error(f"Failed to run meson introspect command: {e}")
            result_code = 1
            result_out = ""

        if result_code != 0:
            error_msg = f"meson introspect failed. Check: {self.meson_builddir}"
            log.error(error_msg)
            raise MesonBuildError(error_msg, result_code)

        try:
            options = json.loads(result_out)
            meson_options = {}
            for opt in options:
                # Only store user options (not built-in)
                if opt.get("section") == "user":
                    meson_options[opt["name"]] = opt["value"]

            # Replace the current meson options with the introspect options
            self.meson_options = meson_options

            log.debug(f"Meson introspect options: {self.meson_options}")
        except Exception as e:
            error_msg = f"Failed to parse meson introspect output: {e}"
            log.error(error_msg)
            raise MesonBuildError(error_msg)
