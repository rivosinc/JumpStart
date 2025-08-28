# SPDX-FileCopyrightText: 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import yaml
from system import functions as system_functions  # noqa

from .diag import DiagBuildUnit


class DiagFactoryError(Exception):
    pass


class DiagFactory:
    """Create and build multiple diagnostics from a YAML description.

    YAML format (expected_fail defaults to 0 if not specified):

    diagnostics:
      <diag_name>:
        source_dir: <path>
        override_meson_options: ["key=value", ...]
        override_diag_attributes: ["attr=value", ...]
        diag_custom_defines: ["NAME=VALUE", ...]
        expected_fail: <int>
    """

    def __init__(
        self,
        build_manifest_yaml: dict,
        root_build_dir: str,
        environment: str,
        toolchain: str,
        rng_seed: Optional[int],
        jumpstart_dir: str,
        keep_meson_builddir: bool,
        jobs: int = 1,
        cli_meson_option_overrides: Optional[List[str]] = None,
        cli_diag_attribute_overrides: Optional[List[str]] = None,
        cli_diag_custom_defines: Optional[List[str]] = None,
        skip_write_manifest: bool = False,
    ) -> None:
        self.build_manifest_yaml = build_manifest_yaml
        self.root_build_dir = os.path.abspath(root_build_dir)
        self.toolchain = toolchain

        # Get the environment object
        try:
            from .environment import get_environment_manager

            env_manager = get_environment_manager()
            self.environment = env_manager.get_environment(environment)
        except Exception as e:
            raise DiagFactoryError(f"Failed to get environment '{environment}': {e}")

        self.jumpstart_dir = jumpstart_dir
        self.keep_meson_builddir = keep_meson_builddir
        try:
            self.jobs = max(1, int(jobs))
        except Exception:
            self.jobs = 1
        self.global_overrides: Dict[str, any] = {}
        self.cli_meson_option_overrides = cli_meson_option_overrides or []
        self.cli_diag_attribute_overrides = cli_diag_attribute_overrides or []
        self.cli_diag_custom_defines = cli_diag_custom_defines or []

        self.skip_write_manifest: bool = bool(skip_write_manifest)

        loaded = self.build_manifest_yaml or {}

        # Validate the provided YAML manifest strictly before proceeding
        self._validate_manifest(loaded)

        self.diagnostics: Dict[str, dict] = loaded["diagnostics"] or {}

        # Create a deterministic RNG for generating diag seeds
        if rng_seed is None:
            factory_rng = random.Random()
        else:
            factory_rng = random.Random(rng_seed)

        # Set rng_seed for each diagnostic if not already specified
        for diag_name, diag_config in self.diagnostics.items():
            if "rng_seed" not in diag_config:
                diag_config["rng_seed"] = factory_rng.randrange(sys.maxsize)

        # Optional global_overrides (already validated)
        self.global_overrides = loaded.get("global_overrides") or {}

        system_functions.create_empty_directory(os.path.abspath(self.root_build_dir))

        self._diag_units: Dict[str, DiagBuildUnit] = {}
        # expected_fail now lives per DiagBuildUnit; no per-factory map
        self._build_repo_manifest_path: Optional[str] = None
        self._run_manifest_path: Optional[str] = None

        if not self.skip_write_manifest:
            self.write_build_repro_manifest()

    def _validate_manifest(self, manifest: dict) -> None:
        """Validate the structure and types of a DiagFactory YAML manifest.

        Rules:
        - Top-level: required key `diagnostics`, optional keys `global_overrides`, `rng_seed`.
          No other top-level keys are allowed.
        - `diagnostics`: mapping of diag_name -> per-diag mapping.
          Each per-diag mapping must include `source_dir` (non-empty string).
          Allowed optional keys per diag: `override_meson_options`, `override_diag_attributes`,
          `diag_custom_defines`, `expected_fail`, `rng_seed`.
        - `global_overrides` (optional): mapping; allowed keys are
          `override_meson_options`, `override_diag_attributes`, `diag_custom_defines`.

        - Types:
          - override_meson_options: dict OR list (each item must be a dict or str)
          - override_diag_attributes: list of str
          - diag_custom_defines: list of str
          - expected_fail: bool, int, or str
          - rng_seed: int

        """
        if not isinstance(manifest, dict):
            raise DiagFactoryError("Invalid diagnostics YAML. Expected a top-level mapping (dict).")

        top_allowed = {"diagnostics", "global_overrides"}
        top_keys = set(manifest.keys())
        if "diagnostics" not in top_keys:
            raise DiagFactoryError("Invalid diagnostics YAML. Missing required key 'diagnostics'.")
        extra_top = top_keys - top_allowed
        if extra_top:
            raise DiagFactoryError(
                "Invalid diagnostics YAML. Only 'diagnostics' and optional 'global_overrides' are allowed; found: "
                + ", ".join(sorted(extra_top))
            )

        diagnostics = manifest.get("diagnostics")
        if not isinstance(diagnostics, dict) or len(diagnostics) == 0:
            raise DiagFactoryError("'diagnostics' must be a non-empty mapping of names to configs.")

        per_diag_allowed = {
            "source_dir",
            "override_meson_options",
            "override_diag_attributes",
            "diag_custom_defines",
            "expected_fail",
            "rng_seed",
        }

        def _validate_override_meson_options(value, context: str) -> None:
            if isinstance(value, dict):
                return
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    if not isinstance(item, (str, dict)):
                        raise DiagFactoryError(
                            f"{context}.override_meson_options[{idx}] must be str or dict"
                        )
                return
            raise DiagFactoryError(f"{context}.override_meson_options must be a dict or list")

        def _validate_str_list(value, context: str, field_name: str) -> None:
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise DiagFactoryError(f"{context}.{field_name} must be a list of strings")

        # Validate each diagnostic block
        for diag_name, diag_cfg in diagnostics.items():
            if not isinstance(diag_name, str) or diag_name.strip() == "":
                raise DiagFactoryError("Each diagnostic name must be a non-empty string")
            if not isinstance(diag_cfg, dict):
                raise DiagFactoryError(
                    f"diagnostics.{diag_name} must be a mapping of options, found {type(diag_cfg).__name__}"
                )

            # Unknown key check
            unknown = set(diag_cfg.keys()) - per_diag_allowed
            if unknown:
                raise DiagFactoryError(
                    f"diagnostics.{diag_name} contains unknown key(s): "
                    + ", ".join(sorted(unknown))
                )

            # Required source_dir
            src = diag_cfg.get("source_dir")
            if not isinstance(src, str) or src.strip() == "":
                raise DiagFactoryError(
                    f"diagnostics.{diag_name}.source_dir is required and must be a non-empty string"
                )

            # Optional per-diag fields
            if "override_meson_options" in diag_cfg:
                _validate_override_meson_options(
                    diag_cfg["override_meson_options"], f"diagnostics.{diag_name}"
                )
            if "override_diag_attributes" in diag_cfg:
                _validate_str_list(
                    diag_cfg["override_diag_attributes"],
                    f"diagnostics.{diag_name}",
                    "override_diag_attributes",
                )
            if "diag_custom_defines" in diag_cfg:
                _validate_str_list(
                    diag_cfg["diag_custom_defines"],
                    f"diagnostics.{diag_name}",
                    "diag_custom_defines",
                )
            if "expected_fail" in diag_cfg:
                ef = diag_cfg["expected_fail"]
                if not isinstance(ef, (bool, int, str)):
                    raise DiagFactoryError(
                        f"diagnostics.{diag_name}.expected_fail must be a bool, int, or str"
                    )
            if "rng_seed" in diag_cfg:
                seed = diag_cfg["rng_seed"]
                if not isinstance(seed, int):
                    raise DiagFactoryError(
                        f"diagnostics.{diag_name}.rng_seed must be an integer if provided"
                    )
                if seed < 0:
                    raise DiagFactoryError(f"diagnostics.{diag_name}.rng_seed must be non-negative")

        # Validate optional global_overrides
        if "global_overrides" in manifest:
            go = manifest["global_overrides"]
            if not isinstance(go, dict):
                raise DiagFactoryError("global_overrides must be a mapping (dict)")
            go_allowed = {
                "override_meson_options",
                "override_diag_attributes",
                "diag_custom_defines",
            }
            unknown = set(go.keys()) - go_allowed
            if unknown:
                raise DiagFactoryError(
                    "global_overrides contains unknown key(s): " + ", ".join(sorted(unknown))
                )
            if "override_meson_options" in go:
                _validate_override_meson_options(go["override_meson_options"], "global_overrides")
            if "override_diag_attributes" in go:
                _validate_str_list(
                    go["override_diag_attributes"],
                    "global_overrides",
                    "override_diag_attributes",
                )
            if "diag_custom_defines" in go:
                _validate_str_list(
                    go["diag_custom_defines"], "global_overrides", "diag_custom_defines"
                )

    def _execute_parallel(
        self,
        max_workers: int,
        tasks: Dict[str, Tuple],
        runner_fn,
    ) -> Dict[str, DiagBuildUnit]:
        """Execute tasks concurrently and return a mapping of diag name to unit.

        - tasks: mapping of diag_name -> tuple where the first element is the DiagBuildUnit
                 followed by any extra args needed by runner_fn.
        - runner_fn: callable invoked as runner_fn(name, *task_args)
        """
        results: Dict[str, DiagBuildUnit] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {}
            for diag_name, args in tasks.items():
                unit = args[0]
                fut = executor.submit(runner_fn, diag_name, *args)
                future_to_task[fut] = (diag_name, unit)

            for fut in as_completed(list(future_to_task.keys())):
                diag_name, unit = future_to_task[fut]
                try:
                    fut.result()
                except Exception:
                    # Any exception is already recorded (or will be) on the unit
                    pass
                results[diag_name] = unit
        return results

    def _normalize_to_kv_list(self, value) -> List[str]:
        """Normalize override structures into a list of "k=v" strings.

        Accepts dict, list of dicts, list of strings, or None.
        """
        if not value:
            return []
        if isinstance(value, dict):
            return [f"{k}={v}" for k, v in value.items()]
        if isinstance(value, list):
            if all(isinstance(x, dict) for x in value):
                merged: Dict[str, any] = {}
                for item in value:
                    merged.update(item)
                return [f"{k}={v}" for k, v in merged.items()]
            return [str(x) for x in value if isinstance(x, str)]
        raise TypeError("Unsupported override format; expected dict or list")

    def _dedupe_kv_list(self, items: List[str]) -> List[str]:
        """Remove duplicate keys from a list of "k=v" strings keeping the last occurrence.

        Preserves the overall order of first appearances after de-duplication.
        """
        seen = {}
        order: List[str] = []
        # Walk from end so later entries win
        for entry in reversed(items or []):
            if "=" in entry:
                key = entry.split("=", 1)[0]
            else:
                key = entry
            if key not in seen:
                seen[key] = entry
                order.append(key)
        # Reconstruct in forward order
        order.reverse()
        return [seen[k] for k in order]

    def build_repro_manifest_dict(self) -> dict:
        """Create a reproducible build manifest combining diagnostics and global overrides.

        Command-line overrides are appended under 'global_overrides'.
        """
        # Start with diagnostics as loaded
        manifest: Dict[str, any] = {"diagnostics": dict(self.diagnostics)}

        # Merge global overrides with CLI overrides
        global_overrides: Dict[str, any] = dict(self.global_overrides or {})

        combined_meson = self._normalize_to_kv_list(global_overrides.get("override_meson_options"))
        combined_meson.extend(list(self.cli_meson_option_overrides or []))
        combined_meson = self._dedupe_kv_list(combined_meson)
        if combined_meson:
            global_overrides["override_meson_options"] = combined_meson

        combined_diag_attrs = self._normalize_to_kv_list(
            global_overrides.get("override_diag_attributes")
        )
        combined_diag_attrs.extend(list(self.cli_diag_attribute_overrides or []))
        combined_diag_attrs = self._dedupe_kv_list(combined_diag_attrs)
        if combined_diag_attrs:
            global_overrides["override_diag_attributes"] = combined_diag_attrs

        existing_defines = global_overrides.get("diag_custom_defines") or []
        if isinstance(existing_defines, dict):
            existing_defines = [f"{k}={v}" for k, v in existing_defines.items()]
        elif isinstance(existing_defines, list):
            existing_defines = [str(x) for x in existing_defines]
        else:
            existing_defines = []
        combined_defines = list(existing_defines)
        combined_defines.extend(list(self.cli_diag_custom_defines or []))
        combined_defines = self._dedupe_kv_list(combined_defines)
        if combined_defines:
            global_overrides["diag_custom_defines"] = combined_defines

        if global_overrides:
            manifest["global_overrides"] = global_overrides

        return manifest

    def write_build_repro_manifest(self, output_path: Optional[str] = None) -> str:
        """Write the build manifest YAML to disk and return its path."""
        if output_path is None:
            output_path = os.path.join(self.root_build_dir, "build_manifest.repro.yaml")
        manifest = self.build_repro_manifest_dict()
        with open(output_path, "w") as f:
            yaml.safe_dump(manifest, f, sort_keys=False)
        self._build_repo_manifest_path = output_path
        log.debug(f"Wrote build manifest: {output_path}")
        return output_path

    def write_run_manifest(self, output_path: Optional[str] = None) -> str:
        """Write the run manifest YAML to disk and return its path.

        Format:
        diagnostics:
          <diag name>:
            elf_path: <path to ELF>
            num_iterations: 1
            expected_fail: <bool>
        """
        if output_path is None:
            output_path = os.path.join(self.root_build_dir, "run_manifest.yaml")

        run_manifest = {"diagnostics": {}}

        # Include all successfully compiled diags
        for diag_name, unit in self._diag_units.items():
            if (
                getattr(unit, "compile_state", None) is not None
                and getattr(unit.compile_state, "name", "") == "PASS"
                and unit.compile_error is None
            ):
                try:
                    elf_path = unit.get_build_asset("elf")
                    if os.path.exists(elf_path):
                        run_manifest["diagnostics"][diag_name] = {
                            "elf_path": os.path.abspath(elf_path),
                            "num_iterations": 1,
                            "expected_fail": getattr(unit, "expected_fail", False),
                        }
                except Exception as exc:
                    log.warning(f"Failed to get ELF path for diag '{diag_name}': {exc}")

        with open(output_path, "w") as f:
            yaml.safe_dump(run_manifest, f, sort_keys=False)
        self._run_manifest_path = output_path
        log.debug(f"Wrote run manifest: {output_path}")
        return output_path

    def _prepare_unit(self, diag_name: str, config: dict) -> Tuple[str, DiagBuildUnit]:
        # Do not validate here; DiagBuildUnit validates presence of 'source_dir'
        # Pass through all per-diag config keys as-is
        yaml_diag_config = dict(config)

        # Create per-diag build dir
        diag_build_dir = os.path.join(self.root_build_dir, diag_name)

        # Build the single YAML config to pass through: { <diag_name>: {..}, global_overrides: {...} }
        # Create deep copies to avoid modifying shared state
        import copy

        merged_yaml_config = {
            diag_name: copy.deepcopy({k: v for k, v in yaml_diag_config.items() if v is not None}),
            "global_overrides": copy.deepcopy(self.global_overrides),
        }

        unit = DiagBuildUnit(
            yaml_config=merged_yaml_config,
            meson_options_cmd_line_overrides=(
                copy.deepcopy(self.cli_meson_option_overrides)
                if self.cli_meson_option_overrides
                else None
            ),
            diag_attributes_cmd_line_overrides=(
                copy.deepcopy(self.cli_diag_attribute_overrides)
                if self.cli_diag_attribute_overrides
                else None
            ),
            diag_custom_defines_cmd_line_overrides=(
                copy.deepcopy(self.cli_diag_custom_defines)
                if self.cli_diag_custom_defines
                else None
            ),
            build_dir=diag_build_dir,
            environment=copy.deepcopy(self.environment),
            toolchain=self.toolchain,
            jumpstart_dir=self.jumpstart_dir,
            keep_meson_builddir=self.keep_meson_builddir,
        )

        return diag_build_dir, unit

    def compile_all(self) -> Dict[str, DiagBuildUnit]:
        def _do_compile(name: str, unit: DiagBuildUnit, build_dir: str) -> None:
            log.info(f"Compiling '{name}'")
            log.debug(f"Build directory: {build_dir}")
            try:
                unit.compile()
            except Exception as exc:
                try:
                    # Capture unexpected exceptions as compile_error
                    unit.compile_error = f"{type(exc).__name__}: {exc}"
                except Exception:
                    pass

        # Build task map: name -> (unit, build_dir)
        tasks: Dict[str, Tuple] = {}
        for diag_name, config in self.diagnostics.items():
            diag_build_dir, unit = self._prepare_unit(diag_name, config)
            self._diag_units[diag_name] = unit
            tasks[diag_name] = (unit, diag_build_dir)

        self._execute_parallel(self.jobs, tasks, _do_compile)

        for name, unit in self._diag_units.items():
            log.debug(f"Diag built details: {unit}")

        # Generate run manifest after all compilation is complete
        if not self.skip_write_manifest:
            self.write_run_manifest()

        # After building all units (and generating any artifacts), raise if any compile failed
        compile_failures = [
            name
            for name, unit in self._diag_units.items()
            if (
                getattr(unit, "compile_state", None) is not None
                and getattr(unit.compile_state, "name", "") == "FAILED"
            )
            or (unit.compile_error is not None)
        ]
        if compile_failures:
            raise DiagFactoryError(
                "One or more diagnostics failed to compile: " + ", ".join(compile_failures)
            )

    def run_all(self) -> Dict[str, DiagBuildUnit]:
        if not self._diag_units:
            raise DiagFactoryError("run_all() called before compile_all().")

        def _do_run(name: str, unit: DiagBuildUnit) -> None:
            log.info(f"Running diag '{name}'")
            try:
                unit.run()
            except Exception as exc:
                try:
                    unit.run_error = f"{type(exc).__name__}: {exc}"
                except Exception:
                    pass

        run_tasks: Dict[str, Tuple] = {name: (unit,) for name, unit in self._diag_units.items()}
        effective_jobs = self.jobs if self.environment.run_target == "spike" else 1
        self._execute_parallel(effective_jobs, run_tasks, _do_run)

        # After running all units, raise if any run failed
        run_failures = [
            name
            for name, unit in self._diag_units.items()
            if (
                (getattr(unit, "run_state", None) is not None and unit.run_state.name == "FAILED")
                or (unit.run_error is not None)
            )
        ]
        if run_failures:
            raise DiagFactoryError(
                "One or more diagnostics failed to run: " + ", ".join(run_failures)
            )

    def summarize(self) -> str:
        # Build pretty table; compute widths from plain text, add ANSI coloring for PASS/FAILED/EXPECTED_FAIL labels

        # Define color constants
        bold = "\u001b[1m"
        reset = "\u001b[0m"
        green = "\u001b[32m"
        red = "\u001b[31m"

        # Gather data per-diag for the Result column
        gathered = []
        for diag_name, unit in self._diag_units.items():
            build_plain = unit.format_build_label(include_duration=True, color=False)
            run_plain = unit.format_run_label(include_duration=True, color=False)
            error_text = unit.compile_error or unit.run_error or ""

            try:
                elf_path = unit.get_build_asset("elf")
            except Exception:
                elf_path = None

            # Determine what to show in the Result column
            if error_text and error_text.strip():
                # If there's an error, show it (will be colored red later)
                merged_content = error_text
            elif elf_path:
                # If no error but ELF is available, show the path
                merged_content = elf_path
            else:
                merged_content = "N/A"

            gathered.append(
                {
                    "name": diag_name,
                    "build": build_plain,
                    "run": run_plain,
                    "result": merged_content,
                    "has_error": bool(error_text and error_text.strip()),
                }
            )

        # Check if Result column would be empty (all "N/A")
        include_result_col = any(item["result"] != "N/A" for item in gathered)

        # Build rows in two-row groups per diag
        row_groups = []
        for item in gathered:
            if include_result_col:
                row_groups.append(
                    [
                        (
                            item["name"],
                            item["build"],
                            item["run"],
                            item["result"],
                            item["has_error"],
                        ),
                    ]
                )
            else:
                row_groups.append(
                    [
                        (
                            item["name"],
                            item["build"],
                            item["run"],
                            item["has_error"],
                        ),
                    ]
                )

        # Header varies depending on whether we include the Result column
        if include_result_col:
            header = ("Diag", "Build", f"Run [{self.environment.run_target}]", "Result")
        else:
            header = ("Diag", "Build", f"Run [{self.environment.run_target}]")

        # Compute column widths based on plain text
        col_widths = [len(h) for h in header]
        for group in row_groups:
            for r in group:
                # Consider the display elements (excluding has_error which is a boolean flag)
                # When include_result_col is True: r has 5 elements, last is has_error
                # When include_result_col is False: r has 4 elements, last is has_error
                display_elements = r[:-1]  # Always exclude the last element (has_error)
                for i, cell in enumerate(display_elements):
                    if len(str(cell)) > col_widths[i]:
                        col_widths[i] = len(str(cell))

        def pad(cell: str, width: int) -> str:
            return cell.ljust(width)

        # Build table lines
        top = "┏" + "┳".join("━" * (w + 2) for w in col_widths) + "┓"
        hdr = "┃ " + " ┃ ".join(pad(h, w) for h, w in zip(header, col_widths)) + " ┃"
        sep = "┡" + "╇".join("━" * (w + 2) for w in col_widths) + "┩"
        inner = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"

        body = []
        for gi, group in enumerate(row_groups):
            for ri, r in enumerate(group):
                # Unpack the row data based on whether we have the result column
                if include_result_col:
                    diag_name, build_plain, run_plain, result, has_error = r
                else:
                    diag_name, build_plain, run_plain, has_error = r

                # pad using plain text
                diag_pad = pad(str(diag_name), col_widths[0])
                build_pad = pad(build_plain, col_widths[1])
                run_pad = pad(run_plain, col_widths[2])

                # colorize status prefixes on the first row of each group only
                unit = self._diag_units.get(diag_name) if ri == 0 else None
                if unit is not None:
                    build_colored = unit.colorize_status_text(build_pad)
                    run_colored = unit.colorize_status_text(run_pad)
                else:
                    build_colored = build_pad
                    run_colored = run_pad

                # Build the row content
                if include_result_col:
                    result_pad = pad(str(result), col_widths[3])
                    # Apply red coloring to errors in the result column
                    if has_error:
                        result_colored = f"{red}{result_pad}{reset}"
                    else:
                        result_colored = result_pad
                    row_content = [diag_pad, build_colored, run_colored, result_colored]
                else:
                    row_content = [diag_pad, build_colored, run_colored]

                body.append("│ " + " │ ".join(row_content) + " │")
            # separator between diagnostics (groups), except after the last group
            if gi != len(row_groups) - 1:
                body.append(inner)
        bot = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"

        # Compute overall result visibility line
        try:
            overall_pass = True
            for _name, _unit in self._diag_units.items():
                if (
                    getattr(_unit, "compile_state", None) is None
                    or _unit.compile_state.name != "PASS"
                ):
                    overall_pass = False
                    break
                if _unit.compile_error is not None:
                    overall_pass = False
                    break
                if getattr(_unit, "run_state", None) is None or _unit.run_state.name == "FAILED":
                    overall_pass = False
                    break
                if _unit.run_error is not None:
                    overall_pass = False
                    break
        except Exception:
            overall_pass = False

        overall_line = (
            f"{bold}{green}STATUS: PASSED{reset}"
            if overall_pass
            else f"{bold}{red}STATUS: FAILED{reset}"
        )

        table_lines = [
            f"\n{bold}Summary{reset}",
            f"Build root: {self.root_build_dir}",
            f"Build Repro Manifest: {self._build_repo_manifest_path}",
            top,
            hdr,
            sep,
            *body,
            bot,
        ]

        # Note: Per-diag artifact section removed; artifacts are shown inline in the table

        # Add Run Manifest before the final status
        table_lines.append(f"\n{bold}Run Manifest{reset}:\n{self._run_manifest_path}")

        # Print overall result at the very end for visibility
        table_lines.append("")
        table_lines.append(overall_line)
        log.info("\n".join(table_lines))
