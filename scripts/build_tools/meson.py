# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import os
import pprint
import shutil
import sys
import tempfile
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
    supported_toolchains: List[str] = ["gcc"]

    def __init__(
        self,
        toolchain: str,
        jumpstart_dir: str,
        diag_name: str,
        diag_sources: List[str],
        diag_attributes_yaml: str,
        boot_config: str,
        keep_meson_builddir: bool,
        buildtype: str,
    ) -> None:
        self.meson_builddir = None
        self.keep_meson_builddir = None

        assert toolchain in self.supported_toolchains
        self.toolchain = toolchain

        if not os.path.exists(jumpstart_dir):
            raise Exception(f"Jumpstart directory does not exist: {jumpstart_dir}")
        self.jumpstart_dir = os.path.abspath(jumpstart_dir)

        self.diag_name = diag_name
        self.buildtype = buildtype

        self.meson_options: Dict[str, Any] = {}

        self.meson_builddir = tempfile.mkdtemp(prefix=f"{self.diag_name}_meson_builddir_")

        self.keep_meson_builddir: bool = keep_meson_builddir

        self.setup_default_meson_options(
            diag_sources,
            diag_attributes_yaml,
            boot_config,
        )

    def __del__(self):
        if self.meson_builddir is not None and self.keep_meson_builddir is False:
            try:
                log.debug(f"Removing meson build directory: {self.meson_builddir}")
                shutil.rmtree(self.meson_builddir)
            except Exception as exc:
                log.debug(f"Ignoring error during meson build directory cleanup: {exc}")

    def setup_default_meson_options(
        self,
        diag_sources: List[str],
        diag_attributes_yaml: str,
        boot_config: str,
    ) -> None:
        self.meson_options["diag_name"] = self.diag_name
        self.meson_options["diag_sources"] = diag_sources
        self.meson_options["diag_attributes_yaml"] = diag_attributes_yaml
        self.meson_options["boot_config"] = boot_config
        self.meson_options["diag_attribute_overrides"] = []

        self.meson_options["buildtype"] = self.buildtype

        self.meson_options["spike_additional_arguments"] = []

        self.trace_file = f"{self.meson_builddir}/{self.diag_name}.itrace"

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
        if self.meson_options["buildtype"] != self.buildtype:
            raise Exception(
                f"Buildtype in meson_options: {self.meson_options['buildtype']} does not match requested buildtype: {self.buildtype}. Always use the command line option to set the --buildtype."
            )

        self.meson_setup_flags = {}
        for option in self.meson_options:
            if isinstance(self.meson_options[option], list):
                if len(self.meson_options[option]) == 0:
                    continue
                self.meson_setup_flags[f"-D{option}"] = (
                    "[" + ",".join(f"'{x}'" for x in self.meson_options[option]) + "]"
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
                f"cross_compile/public/{self.toolchain}_options.txt",
                "--cross-file",
                f"cross_compile/{self.toolchain}.txt",
            ]
        )

        log.debug("Meson options:\n%s", self.get_meson_options_pretty(spacing="\t"))

        # Print the meson setup command in a format that can be copy-pasted to
        # reproduce the build.
        printable_meson_setup_command = " ".join(meson_setup_command)
        printable_meson_setup_command = printable_meson_setup_command.replace("'", "\\'")
        log.info(f"Running meson setup.\n{printable_meson_setup_command}")
        return_code = system_functions.run_command(meson_setup_command, self.jumpstart_dir)
        if return_code != 0:
            error_msg = f"Meson setup failed for diag: {self.diag_name}. Check the meson build directory for more information: {self.meson_builddir}"
            log.error(error_msg)
            self.keep_meson_builddir = True
            raise MesonBuildError(error_msg, return_code)

    def compile(self):
        meson_compile_command = ["meson", "compile", "-v", "-C", self.meson_builddir]
        log.info(f"Running meson compile.\n{' '.join(meson_compile_command)}")
        return_code = system_functions.run_command(meson_compile_command, self.jumpstart_dir)

        diag_binary = os.path.join(self.meson_builddir, self.diag_name + ".elf")
        diag_disasm = os.path.join(self.meson_builddir, self.diag_name + ".dis")

        if return_code == 0:
            if not os.path.exists(diag_binary):
                error_msg = f"diag binary: {diag_binary} not created by meson compile"
                self.keep_meson_builddir = True
                raise MesonBuildError(error_msg)

        if return_code != 0:
            error_msg = f"meson compile failed for diag: {self.diag_name}"
            log.error(error_msg)
            self.keep_meson_builddir = True
            raise MesonBuildError(error_msg, return_code)

        compiled_assets = {}
        if os.path.exists(diag_disasm):
            compiled_assets["disasm"] = diag_disasm
        if os.path.exists(diag_binary):
            compiled_assets["binary"] = diag_binary
        return compiled_assets

    def test(self):
        meson_test_command = ["meson", "test", "-v", "-C", self.meson_builddir]
        log.info(f"Running meson test.\n{' '.join(meson_test_command)}")
        return_code = system_functions.run_command(meson_test_command, self.jumpstart_dir)

        run_assets = {}

        generate_trace = bool(self.meson_options.get("generate_trace", False))
        if generate_trace:
            if return_code == 0 and not os.path.exists(self.trace_file):
                error_msg = (
                    f"meson test passed but trace file not created by diag: {self.trace_file}"
                )
                self.keep_meson_builddir = True
                raise MesonBuildError(error_msg)

            run_assets["trace"] = self.trace_file
        elif self.trace_file and os.path.exists(self.trace_file):
            error_msg = (
                f"Trace generation was disabled but trace file was created: {self.trace_file}"
            )
            self.keep_meson_builddir = True
            raise MesonBuildError(error_msg)

        if return_code != 0:
            error_msg = f"meson test failed for diag: {self.diag_name}.\nPartial diag build assets may have been generated in {self.meson_builddir}\n"
            log.error(error_msg)
            self.keep_meson_builddir = True
            raise MesonBuildError(error_msg, return_code)

        return run_assets
