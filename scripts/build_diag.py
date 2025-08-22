#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Builds a diag executable given a source directory containing a jumpstart diag.

import argparse
import logging as log
import os
from typing import Dict

import yaml
from build_tools import DiagBuildUnit, DiagFactory, Meson
from build_tools.environment import get_environment_manager


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jumpstart_dir",
        help="Jumpstart directory",
        required=False,
        type=str,
        default=f"{os.path.dirname(os.path.realpath(__file__))}/..",
    )
    # Allow either a list of source directories or a YAML manifest
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "--diag_src_dir",
        "-d",
        "--diag_src",
        help="One or more directories containing jumpstart diags to build. If provided, a YAML plan will be generated automatically.",
        nargs="+",
        type=str,
    )
    input_group.add_argument(
        "--build_manifest",
        help="Path to a YAML manifest with a top-level 'diagnostics' mapping for DiagFactory.",
        type=str,
    )
    parser.add_argument(
        "--include_diags",
        help=(
            "Limit build to only the specified diagnostics present in the provided build manifest. "
            "Only valid with --build_manifest and incompatible with --diag_src_dir."
        ),
        nargs="+",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--exclude_diags",
        help=(
            "Exclude the specified diagnostics from the provided build manifest. "
            "Only valid with --build_manifest and incompatible with --diag_src_dir."
        ),
        nargs="+",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--buildtype",
        help="--buildtype to pass to meson setup.",
        type=str,
        default=None,
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

    env_manager = get_environment_manager()
    env_names = sorted(env_manager.list_visible_environments().keys())
    env_help = f"Environment to build for. Available environments: {', '.join(env_names)}"

    parser.add_argument(
        "--environment",
        "-e",
        help=env_help,
        required=False,
        type=str,
        default=None,
        choices=env_names,
    )
    parser.add_argument(
        "--target",
        "-t",
        help="[DEPRECATED] Use --environment instead. Target to build for.",
        required=False,
        type=str,
        default=None,
        choices=env_names,
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
        help=f"Boot Config to build diag for. Options: {DiagBuildUnit.supported_boot_configs}.",
        required=False,
        type=str,
        default="fw-none",
        choices=DiagBuildUnit.supported_boot_configs,
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
        required=False,
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
    parser.add_argument(
        "-j",
        "--jobs",
        help="Number of parallel compile jobs.",
        required=False,
        type=int,
        default=5,
    )
    args = parser.parse_args()

    # Handle backward compatibility for --target
    if args.target is not None:
        import warnings

        warnings.warn(
            "--target is deprecated and will be removed in a future version. Use --environment instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # If both --target and --environment are specified, error out
        if args.environment is not None:
            parser.error(
                "Cannot specify both --target and --environment. Use --environment instead."
            )
        # Use target value as environment if environment is not specified
        args.environment = args.target

    # Validate required arguments for normal operation
    if not args.diag_src_dir and not args.build_manifest:
        parser.error("Either --diag_src_dir or --build_manifest is required")

    if not args.diag_build_dir:
        parser.error("--diag_build_dir is required")

    if args.environment is None:
        parser.error("--environment must be specified")

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

    if args.buildtype is not None:
        args.override_meson_options.append(f"buildtype={args.buildtype}")

    if args.active_cpu_mask_override is not None:
        args.override_diag_attributes.append(f"active_cpu_mask={args.active_cpu_mask_override}")

    # Enforce argument compatibility for include/exclude options
    if args.include_diags is not None and args.build_manifest is None:
        raise SystemExit("--include_diags can only be used with --build_manifest.")
    if args.exclude_diags is not None and args.build_manifest is None:
        raise SystemExit("--exclude_diags can only be used with --build_manifest.")

    # Determine the build manifest YAML path: either provided manifest or a generated plan
    build_manifest_yaml = None
    if args.build_manifest is not None:
        build_manifest_yaml_file = os.path.abspath(args.build_manifest)
        build_manifest_yaml = yaml.safe_load(open(build_manifest_yaml_file))
        if args.include_diags is not None or args.exclude_diags is not None:
            if (
                not isinstance(build_manifest_yaml, dict)
                or "diagnostics" not in build_manifest_yaml
            ):
                raise SystemExit(
                    "Provided build manifest is missing the required top-level 'diagnostics' mapping"
                )
            diagnostics_full = build_manifest_yaml.get("diagnostics", {})
            filtered_diags = diagnostics_full.copy()
            # Apply include first (if provided)
            if args.include_diags is not None:
                filtered_diags = {}
                for diag_name in args.include_diags:
                    if diag_name not in diagnostics_full:
                        raise SystemExit(
                            f"--include_diags specified '{diag_name}' which is not present in the provided build manifest"
                        )
                    filtered_diags[diag_name] = diagnostics_full[diag_name]
            # Then apply exclude (if provided)
            if args.exclude_diags is not None:
                for diag_name in args.exclude_diags:
                    if diag_name not in diagnostics_full:
                        raise SystemExit(
                            f"--exclude_diags specified '{diag_name}' which is not present in the provided build manifest"
                        )
                    if diag_name in filtered_diags:
                        del filtered_diags[diag_name]
            build_manifest_yaml["diagnostics"] = filtered_diags
    else:
        # Use the directory name as the diag name (no disambiguation) and error on duplicates
        diag_name_to_dir: Dict[str, str] = {}
        for path in args.diag_src_dir:
            name = os.path.basename(os.path.normpath(path)) or "diag"
            if name in diag_name_to_dir:
                existing = diag_name_to_dir[name]
                raise SystemExit(
                    f"Found multiple diags with the same name derived from directory basenames. Please ensure unique names. Conflict: {name}: [{existing}, {path}]"
                )
            diag_name_to_dir[name] = path

        build_manifest_yaml = {"diagnostics": {}}
        for diag_name, src_dir in diag_name_to_dir.items():
            build_manifest_yaml["diagnostics"][diag_name] = {"source_dir": src_dir}

    # Add the script default to the meson options in the build manifest.
    for key, value in script_meson_option_overrides.items():
        if "global_overrides" not in build_manifest_yaml:
            build_manifest_yaml["global_overrides"] = {}
        if "override_meson_options" not in build_manifest_yaml["global_overrides"]:
            build_manifest_yaml["global_overrides"]["override_meson_options"] = []
        build_manifest_yaml["global_overrides"]["override_meson_options"].insert(
            0, f"{key}={value}"
        )

    factory = DiagFactory(
        build_manifest_yaml=build_manifest_yaml,
        root_build_dir=args.diag_build_dir,
        environment=args.environment,
        toolchain=args.toolchain,
        boot_config=args.boot_config,
        rng_seed=args.rng_seed,
        jumpstart_dir=args.jumpstart_dir,
        keep_meson_builddir=args.keep_meson_builddir,
        jobs=args.jobs,
        cli_meson_option_overrides=args.override_meson_options,
        cli_diag_attribute_overrides=args.override_diag_attributes,
        cli_diag_custom_defines=args.diag_custom_defines,
    )

    try:
        factory.compile_all()

        if args.disable_diag_run is False:
            factory.run_all()
    except Exception as exc:
        # Ensure we always print a summary before exiting
        try:
            factory.summarize()
        except Exception:
            pass
        log.error(str(exc))
        raise SystemExit(1)

    factory.summarize()


if __name__ == "__main__":
    main()
