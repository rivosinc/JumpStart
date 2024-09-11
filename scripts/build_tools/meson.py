# SPDX-FileCopyrightText: 2023 - 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import os
import random
import shutil
import sys
import tempfile

import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from data_structures import DictUtils  # noqa
from system import functions as system_functions  # noqa


def convert_hart_mask_to_num_active_harts(hart_mask):
    num_harts = 0
    hart_mask = int(hart_mask, 2)
    while hart_mask != 0:
        # We don't expect gaps in the hart mask at this point.
        assert hart_mask & 1
        num_harts += 1
        hart_mask >>= 1
    return num_harts


class Meson:
    def __init__(
        self,
        jumpstart_dir,
        diag_build_target,
        keep_meson_builddir,
    ) -> None:
        self.meson_builddir = None
        self.keep_meson_builddir = None

        if not os.path.exists(jumpstart_dir):
            raise Exception(f"Jumpstart directory does not exist: {jumpstart_dir}")

        self.jumpstart_dir = os.path.abspath(jumpstart_dir)

        self.diag_build_target = diag_build_target

        self.diag_binary_name = self.diag_build_target.diag_source.diag_name + ".elf"

        self.meson_options = {}

        self.meson_builddir = tempfile.mkdtemp(
            prefix=f"{self.diag_build_target.diag_source.diag_name}_meson_builddir_"
        )

        self.keep_meson_builddir = keep_meson_builddir

        system_functions.create_empty_directory(self.diag_build_target.build_dir)

        if self.diag_build_target.rng_seed is None:
            self.diag_build_target.rng_seed = random.randrange(sys.maxsize)
        log.debug(
            f"Diag: {self.diag_build_target.diag_source.diag_name} Seeding builder RNG with: {self.diag_build_target.rng_seed}"
        )
        self.rng = random.Random(self.diag_build_target.rng_seed)

    def __del__(self):
        if self.meson_builddir is not None and self.keep_meson_builddir is False:
            log.debug(f"Removing meson build directory: {self.meson_builddir}")
            shutil.rmtree(self.meson_builddir)

    def get_active_hart_mask(self):
        active_hart_mask = None

        # 1. If the diag has an active_hart_mask defined, set active_hart_mask to that.
        active_hart_mask = self.diag_build_target.diag_source.active_hart_mask

        # NOTE: The active_hart_mask can only be overriden if allow_active_hart_mask_override is set to True in the diag.
        # 2. If the --active_hart_mask_override is specified on the command line, set active_hart_mask to active_hart_mask_override.
        if self.diag_build_target.active_hart_mask_override is not None:
            if active_hart_mask is not None:
                log.warning(
                    f"Overriding active_hart_mask {active_hart_mask} with: {self.diag_build_target.active_hart_mask_override}"
                )
            active_hart_mask = self.diag_build_target.active_hart_mask_override

        return active_hart_mask

    def setup_default_meson_options(self):
        self.meson_options["diag_name"] = self.diag_binary_name
        self.meson_options["diag_sources"] = self.diag_build_target.diag_source.get_sources()
        self.meson_options["diag_attributes_yaml"] = (
            self.diag_build_target.diag_source.get_diag_attributes_yaml()
        )
        self.meson_options["boot_config"] = self.diag_build_target.boot_config
        self.meson_options["diag_attribute_overrides"] = []

        self.meson_options["spike_additional_arguments"] = []

        self.meson_options["diag_target"] = self.diag_build_target.target
        if self.diag_build_target.target == "spike":
            self.meson_options["spike_binary"] = "spike"
            self.meson_options["generate_trace"] = "true"

            self.trace_file = (
                f"{self.meson_builddir}/{self.diag_build_target.diag_source.diag_name}.spike.trace"
            )
            self.meson_options["spike_additional_arguments"].append(f"--log={self.trace_file}")

        elif self.diag_build_target.target == "qemu":
            self.meson_options["qemu_additional_arguments"] = []

            trace_file_name = f"{self.diag_build_target.diag_source.diag_name}.qemu.trace"
            self.trace_file = f"{self.meson_builddir}/{trace_file_name}"

            self.meson_options["qemu_additional_arguments"].extend(
                [
                    "--var",
                    f"out:{self.meson_builddir}",
                    "--var",
                    f"ap-logfile:{trace_file_name}",
                ]
            )
        else:
            raise Exception(f"Unknown target: {self.diag_build_target.target}")

        active_hart_mask = self.get_active_hart_mask()
        if active_hart_mask is not None:
            self.meson_options["diag_attribute_overrides"].append(
                f"active_hart_mask={active_hart_mask}"
            )
            if self.diag_build_target.target == "spike":
                self.meson_options["spike_additional_arguments"].append(
                    f"-p{convert_hart_mask_to_num_active_harts(active_hart_mask)}"
                )

        if self.diag_build_target.diag_attributes_cmd_line_overrides is not None:
            self.meson_options["diag_attribute_overrides"].extend(
                self.diag_build_target.diag_attributes_cmd_line_overrides
            )

    def apply_meson_option_overrides_from_diag(self):
        if self.diag_build_target.diag_source.get_meson_options_override_yaml() is not None:
            with open(self.diag_build_target.diag_source.get_meson_options_override_yaml()) as f:
                meson_option_overrides = yaml.safe_load(f)
                DictUtils.override_dict(self.meson_options, meson_option_overrides, False, True)

    def apply_meson_option_overrides_from_cmd_line(self):
        if self.diag_build_target.meson_options_cmd_line_overrides is not None:
            DictUtils.override_dict(
                self.meson_options,
                DictUtils.create_dict(self.diag_build_target.meson_options_cmd_line_overrides),
                False,
                True,
            )

    def setup(self):
        log.info(
            f"Running meson setup for diag: {self.diag_build_target.diag_source.get_diag_src_dir()}"
        )

        self.meson_setup_flags = {}
        self.meson_setup_flags["--buildtype"] = self.diag_build_target.buildtype
        self.meson_setup_flags["-Ddiag_generate_disassembly"] = "true"

        self.setup_default_meson_options()
        self.apply_meson_option_overrides_from_diag()
        self.apply_meson_option_overrides_from_cmd_line()

        for option in self.meson_options:
            if isinstance(self.meson_options[option], list):
                if len(self.meson_options[option]) == 0:
                    continue
                self.meson_setup_flags[f"-D{option}"] = (
                    "[" + ",".join(f"'{x}'" for x in self.meson_options[option]) + "]"
                )
            else:
                self.meson_setup_flags[f"-D{option}"] = self.meson_options[option]

        meson_setup_command = ["meson", "setup", self.meson_builddir]
        for flag in self.meson_setup_flags:
            meson_setup_command.append(f"{flag}={self.meson_setup_flags[flag]}")

        meson_setup_command.extend(
            [
                "--cross-file",
                f"cross_compile/public/{self.diag_build_target.toolchain}_options.txt",
                "--cross-file",
                f"cross_compile/{self.diag_build_target.toolchain}.txt",
            ]
        )

        log.debug(f"Running meson setup command: {meson_setup_command}")
        return_code = system_functions.run_command(meson_setup_command, self.jumpstart_dir)
        if return_code != 0:
            log.error(
                f"Meson setup failed for diag: {self.diag_build_target.diag_source.diag_name}"
            )
            sys.exit(return_code)

        if self.keep_meson_builddir is True:
            self.diag_build_target.add_build_asset(
                "meson_builddir", self.meson_builddir, None, True
            )

    def compile(self):
        log.info(
            f"Running meson compile for diag: {self.diag_build_target.diag_source.get_diag_src_dir()}"
        )

        meson_compile_command = ["meson", "compile", "-C", self.meson_builddir]
        return_code = system_functions.run_command(meson_compile_command, self.jumpstart_dir)

        diag_binary = os.path.join(self.meson_builddir, self.diag_binary_name)
        diag_disasm = os.path.join(self.meson_builddir, self.diag_binary_name + ".dis")

        if return_code == 0:
            if not os.path.exists(diag_binary):
                raise Exception("diag binary not created by meson compile")

            if not os.path.exists(diag_disasm):
                raise Exception("diag disasm not created by meson compile")

        # We've already checked that these exist for the passing case.
        # They may not exist if the compile failed so check that they
        # exist before copying them. Allows us to get partial build assets.
        if os.path.exists(diag_disasm):
            self.diag_build_target.add_build_asset("disasm", diag_disasm)
        if os.path.exists(diag_binary):
            self.diag_build_target.add_build_asset("binary", diag_binary)

        if return_code != 0:
            log.error(
                f"meson compile failed for diag: {self.diag_build_target.diag_source.diag_name}"
            )
            sys.exit(return_code)

        log.debug(f"Diag compiled: {self.diag_build_target.get_build_asset('binary')}")
        log.debug(f"Diag disassembly: {self.diag_build_target.get_build_asset('disasm')}")

    def test(self):
        log.info(
            f"Running meson test for diag: {self.diag_build_target.diag_source.get_diag_src_dir()}"
        )

        meson_test_command = ["meson", "test", "-C", self.meson_builddir]
        return_code = system_functions.run_command(meson_test_command, self.jumpstart_dir)

        if return_code == 0 and not os.path.exists(self.trace_file):
            raise Exception(
                f"meson test passed but trace file not created by diag: {self.trace_file}"
            )

        self.diag_build_target.add_build_asset("trace", self.trace_file)
        log.debug(f"Diag trace file: {self.diag_build_target.get_build_asset('trace')}")

        if return_code != 0:
            log.error(
                f"meson test failed for diag: {self.diag_build_target.diag_source.diag_name}.\nPartial diag build assets may have been generated in {self.diag_build_target.build_dir}\n"
            )
            sys.exit(return_code)

    def get_generated_diag(self):
        return self.diag_build_target


def build_jumpstart_diag(
    jumpstart_dir,
    diag_build_target,
    disable_diag_run=False,
    keep_meson_builddir=False,
):
    meson = Meson(jumpstart_dir, diag_build_target, keep_meson_builddir)

    meson.setup()
    meson.compile()

    if disable_diag_run is True:
        log.warning(
            f"Skipping running diag {diag_build_target.diag_source.diag_name} on target {diag_build_target.target} as diag run is disabled."
        )
    else:
        meson.test()

    return meson.get_generated_diag()
