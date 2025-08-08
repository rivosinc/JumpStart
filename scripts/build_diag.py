#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Builds a diag executable given a source directory containing a jumpstart diag.

import argparse
import logging as log
import os

from build_tools import DiagBuildTarget, Meson


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jumpstart_dir",
        help="Jumpstart directory",
        required=False,
        type=str,
        default=f"{os.path.dirname(os.path.realpath(__file__))}/..",
    )
    parser.add_argument(
        "--diag_src_dir",
        "-d",
        "--diag_src",
        help="Directory containing jumpstart diag to build.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--buildtype",
        help="--buildtype to pass to meson setup.",
        type=str,
        default="release",
        choices=["release", "minsize", "debug", "debugoptimized"],
    )
    parser.add_argument(
        "--override_meson_options",
        "--override_meson",
        help="Override the meson options from meson.options.",
        required=False,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--override_diag_attributes",
        help="Override the diag attributes specified in the diag's attributes file.",
        required=False,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--diag_custom_defines",
        help="Set diag specific defines.",
        required=False,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--active_cpu_mask_override",
        "-c",
        help="Override the default CPU mask for the diag.",
        required=False,
        type=str,
        default=None,
    )
    parser.add_argument(
        "--target",
        "-t",
        help="Target to build for.",
        required=False,
        type=str,
        default="spike",
        choices=DiagBuildTarget.supported_targets,
    )
    parser.add_argument(
        "--toolchain",
        help=f"Toolchain to build diag with. Options: {Meson.supported_toolchains}.",
        required=False,
        type=str,
        default="gcc",
        choices=Meson.supported_toolchains,
    )
    parser.add_argument(
        "--boot_config",
        help=f"Boot Config to build diag for. Options: {DiagBuildTarget.supported_boot_configs}.",
        required=False,
        type=str,
        default="fw-none",
        choices=DiagBuildTarget.supported_boot_configs,
    )
    parser.add_argument(
        "--disable_diag_run",
        help="Build the diag but don't run it on the target to generate the trace.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--diag_build_dir",
        "--diag_build",
        help="Directory to place built diag in.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--keep_meson_builddir",
        help="Keep the meson build directory.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--rng_seed",
        help="RNG seed for the diag builder.",
        required=False,
        type=lambda x: int(x, 0),
        default=None,
    )
    parser.add_argument(
        "-v", "--verbose", help="Verbose output.", action="store_true", default=False
    )
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.DEBUG)
    else:
        log.basicConfig(format="%(levelname)s: [%(threadName)s]: %(message)s", level=log.INFO)

    script_meson_option_overrides = {
        "generate_trace": "true",
        "diag_generate_disassembly": "true",
    }

    if args.diag_custom_defines:
        script_meson_option_overrides["diag_custom_defines"] = ",".join(args.diag_custom_defines)

    # Only add script defaults for options that haven't been explicitly overridden
    for key, value in script_meson_option_overrides.items():
        if not any(key in override for override in args.override_meson_options):
            args.override_meson_options.append(f"{key}={value}")

    if args.active_cpu_mask_override is not None:
        args.override_diag_attributes.append(f"active_cpu_mask={args.active_cpu_mask_override}")
    diag_build_target = DiagBuildTarget(
        args.diag_src_dir,
        args.diag_build_dir,
        args.target,
        args.toolchain,
        args.buildtype,
        args.boot_config,
        args.rng_seed,
        args.jumpstart_dir,
        args.override_meson_options,
        args.override_diag_attributes,
        args.keep_meson_builddir,
    )

    diag_build_target.compile()

    if args.disable_diag_run is False:
        diag_build_target.run()

    log.info(f"Diag built: {diag_build_target}")


if __name__ == "__main__":
    main()
