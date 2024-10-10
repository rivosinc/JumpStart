#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Builds a diag executable given a source directory containing a jumpstart diag.

import argparse
import logging as log
import os

from build_tools import DiagBuildTarget, build_jumpstart_diag


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
        help="Directory containing jumpstart diag to build.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--buildtype",
        help="--buildtype to pass to meson setup.",
        type=str,
        default="release",
        choices=["release", "debug"],
    )
    parser.add_argument(
        "--override_meson_options",
        help="Override the meson options from meson.options.",
        required=False,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--override_diag_attributes",
        help="Override the diag attributes specified in the diag's attributes file.",
        required=False,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--active_hart_mask_override",
        "-c",
        help="Override the default hart mask for the diag.",
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
        help=f"Toolchain to build diag with. Options: {DiagBuildTarget.supported_toolchains}.",
        required=False,
        type=str,
        default="gcc",
        choices=DiagBuildTarget.supported_toolchains,
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

    diag_build_target = DiagBuildTarget(
        args.diag_src_dir,
        args.diag_build_dir,
        args.buildtype,
        args.target,
        args.toolchain,
        args.boot_config,
        args.rng_seed,
        args.active_hart_mask_override,
        args.override_meson_options,
        args.override_diag_attributes,
    )

    generated_diag = build_jumpstart_diag(
        args.jumpstart_dir,
        diag_build_target,
        args.disable_diag_run,
        args.keep_meson_builddir,
    )

    log.info(f"Diag built: {generated_diag}")


if __name__ == "__main__":
    main()
