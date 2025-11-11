# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import os
import random
import shutil
import time
from typing import Any, List, Optional

import yaml
from system import functions as system_functions  # noqa
from utils.binary_utils import generate_padded_binary_from_elf

from .meson import Meson, MesonBuildError  # noqa


def convert_cpu_mask_to_num_active_cpus(cpu_mask):
    num_cpus = 0
    cpu_mask = int(cpu_mask, 2)
    while cpu_mask != 0:
        num_cpus += 1
        cpu_mask >>= 1
    return num_cpus


class DiagSource:
    source_file_extensions = [".c", ".S"]
    diag_attribute_yaml_extensions = [
        ".diag_attributes.yaml",
        ".diag_attributes.yml",
    ]
    meson_options_override_yaml_extensions = ["meson_option_overrides.yaml"]

    def __init__(self, diag_src_dir: str) -> None:
        self.diag_src_dir = os.path.abspath(diag_src_dir)
        if not os.path.exists(self.diag_src_dir):
            raise Exception(f"Diag source directory does not exist: {self.diag_src_dir}")

        self.diag_sources: List[str] = system_functions.find_files_with_extensions_in_dir(
            self.diag_src_dir, self.source_file_extensions
        )
        if len(self.diag_sources) == 0:
            raise Exception(
                f"Could not find any source files ({self.source_file_extensions}) in diag source directory: {self.diag_src_dir}"
            )

        self.diag_attributes_yaml = system_functions.find_files_with_extensions_in_dir(
            self.diag_src_dir, self.diag_attribute_yaml_extensions
        )
        if len(self.diag_attributes_yaml) == 0:
            raise Exception(
                f"Could not find a diag attributes file in diag source directory {self.diag_src_dir}"
            )
        elif len(self.diag_attributes_yaml) > 1:
            raise Exception(
                f"Expected a single diag attributes file ({self.diag_attribute_yaml_extensions}) but found multiple files ending with {self.diag_attribute_yaml_extensions}: {self.diag_attributes_yaml}"
            )
        self.diag_attributes_yaml = self.diag_attributes_yaml[0]

        self.meson_options_override_yaml: Optional[str] = (
            system_functions.find_files_with_extensions_in_dir(
                self.diag_src_dir, self.meson_options_override_yaml_extensions
            )
        )
        if len(self.meson_options_override_yaml) > 1:
            raise Exception(
                f"Found multiple meson options files: {self.meson_options_override_yaml}"
            )
        elif len(self.meson_options_override_yaml) == 1:
            self.meson_options_override_yaml = self.meson_options_override_yaml[0]
        else:
            self.meson_options_override_yaml = None

    def __str__(self) -> str:
        return f"\t\tDiag: Source Path: {self.diag_src_dir}\n\t\tSources: {self.diag_sources}\n\t\tAttributes: {self.diag_attributes_yaml}\n\t\tMeson options overrides file: {self.meson_options_override_yaml}"

    def get_diag_src_dir(self) -> str:
        return self.diag_src_dir

    def get_sources(self) -> List[str]:
        return self.diag_sources

    def get_diag_attributes_yaml(self) -> str:
        return self.diag_attributes_yaml

    def get_meson_options_override_yaml(self) -> Optional[str]:
        return self.meson_options_override_yaml

    def is_valid_source_directory(diag_src_dir: str) -> bool:
        # if we can successfully make an object without taking an
        # exception then we have a valid diag source directory.
        try:
            DiagSource(diag_src_dir)
        except Exception:
            return False

        return True

    def get_attribute_value(self, attribute_name: str) -> Optional[Any]:
        with open(self.get_diag_attributes_yaml()) as f:
            diag_attributes = yaml.safe_load(f) or {}
            return diag_attributes.get(attribute_name)


class AssetAction(enum.IntEnum):
    MOVE = 0
    COPY = 1
    NO_COPY = 2


class DiagBuildUnit:
    supported_targets = ["spike"]
    supported_boot_configs = ["fw-none"]

    def __init__(
        self,
        yaml_config: dict,
        meson_options_cmd_line_overrides,
        diag_attributes_cmd_line_overrides,
        diag_custom_defines_cmd_line_overrides,
        build_dir,
        target,
        toolchain,
        boot_config,
        rng_seed,
        jumpstart_dir,
        keep_meson_builddir,
    ) -> None:
        self.state = enum.Enum("BuildState", "INITIALIZED COMPILED RUN")
        self.current_state = self.state.INITIALIZED
        # Fine-grained status tracking
        self.CompileState = enum.Enum("CompileState", "PENDING PASS FAILED")
        self.RunState = enum.Enum("RunState", "PENDING PASS CONDITIONAL_PASS EXPECTED_FAIL FAILED")
        self.compile_state = self.CompileState.PENDING
        self.run_state = self.RunState.PENDING
        self.compile_error: Optional[str] = None
        self.run_error: Optional[str] = None
        self.expected_fail: bool = False
        self.compile_duration_s: Optional[float] = None
        self.run_duration_s: Optional[float] = None
        self.run_return_code: Optional[int] = None
        self.build_assets = {}

        # Resolve diag source directory from YAML config only
        if yaml_config is None:
            raise Exception("yaml_config is required for DiagBuildUnit")
        # yaml_config must be of the form { <diag_name>: {...}, global_overrides: {...}? }
        diag_blocks = {k: v for k, v in yaml_config.items() if k != "global_overrides"}
        if len(diag_blocks) != 1:
            raise Exception("Expected exactly one per-diag block in yaml_config")
        # Extract the diag name and its config block
        self.name, only_block = next(iter(diag_blocks.items()))
        resolved_src_dir = only_block.get("source_dir")
        if resolved_src_dir is None:
            raise Exception(
                "Diag source directory not provided. Expected 'source_dir' in per-diag YAML."
            )
        self.diag_source: DiagSource = DiagSource(resolved_src_dir)

        # expected_fail can be provided per-diag in the manifest
        def _coerce_bool(value) -> bool:
            if value is None:
                return False
            if isinstance(value, bool):
                return value
            try:
                if isinstance(value, (int, float)):
                    return bool(value)
                val_str = str(value).strip().lower()
                if val_str in ("true", "yes", "y", "1"):
                    return True
                if val_str in ("false", "no", "n", "0"):
                    return False
                return bool(val_str)
            except Exception:
                return False

        self.expected_fail: bool = _coerce_bool(only_block.get("expected_fail", False))

        assert target in self.supported_targets
        self.target: str = target

        assert rng_seed is not None
        self.rng_seed: int = rng_seed
        log.debug(f"DiagBuildUnit: {self.name} Seeding RNG with: {self.rng_seed}")
        self.rng: random.Random = random.Random(self.rng_seed)

        assert boot_config in self.supported_boot_configs
        self.boot_config: str = boot_config

        if self.target == "spike" and self.boot_config != "fw-none":
            raise Exception(
                f"Invalid boot_config {self.boot_config} for spike. Only fw-none is supported for spike."
            )

        diag_attributes_cmd_line_overrides = diag_attributes_cmd_line_overrides or []

        self.build_dir: str = os.path.abspath(build_dir)
        system_functions.create_empty_directory(self.build_dir)

        # Create a directory for Meson build artifacts inside the diag build directory
        meson_artifacts_dir = os.path.join(self.build_dir, "meson_artifacts")
        system_functions.create_empty_directory(meson_artifacts_dir)

        self.meson = Meson(
            toolchain,
            jumpstart_dir,
            self.name,
            self.diag_source.get_sources(),
            self.diag_source.get_diag_attributes_yaml(),
            self.boot_config,
            keep_meson_builddir,
            meson_artifacts_dir,
        )

        # Start applying meson option overrides.

        # Default meson option overrides for run targets
        self.meson.override_meson_options_from_dict({"diag_target": self.target})

        self.meson.override_meson_options_from_dict(
            {"diag_attribute_overrides": [f"build_rng_seed={self.rng_seed}"]}
        )

        # Meson option overrides from diag's YAML file in source directory.
        meson_yaml_path = self.diag_source.get_meson_options_override_yaml()
        if meson_yaml_path is not None:
            with open(meson_yaml_path) as f:
                overrides_from_yaml = yaml.safe_load(f)
            self.meson.override_meson_options_from_dict(overrides_from_yaml)

        # Apply overrides in order: global (YAML), diag-specific (YAML), command-line

        def _normalize_meson_overrides(value) -> dict:
            if value is None:
                return {}
            # Accept dict, list of "k=v" strings, or list of dicts
            if isinstance(value, dict):
                return value
            if isinstance(value, list):
                # list of dicts
                if all(isinstance(x, dict) for x in value):
                    merged: dict = {}
                    for item in value:
                        merged.update(item)
                    return merged
                # list of strings
                from data_structures import DictUtils  # local import to avoid cycles

                str_items = [x for x in value if isinstance(x, str)]
                return DictUtils.create_dict(str_items)
            raise TypeError("Unsupported override_meson_options format in YAML overrides")

        def _apply_yaml_overrides(overrides: Optional[dict]):
            if not overrides:
                return
            # meson options
            meson_over = _normalize_meson_overrides(overrides.get("override_meson_options"))
            if meson_over:
                self.meson.override_meson_options_from_dict(meson_over)

            # diag_custom_defines
            diag_custom_defines = overrides.get("diag_custom_defines")
            if diag_custom_defines:
                self.meson.override_meson_options_from_dict(
                    {"diag_custom_defines": list(diag_custom_defines)}
                )

            # diag attribute overrides
            diag_attr_overrides = overrides.get("override_diag_attributes")
            if diag_attr_overrides:
                self.meson.override_meson_options_from_dict(
                    {"diag_attribute_overrides": list(diag_attr_overrides)}
                )

        # 1) Global overrides from YAML (if provided as part of yaml_config)
        _apply_yaml_overrides(yaml_config.get("global_overrides"))

        # 2) Diag-specific overrides from YAML (full per-diag block)
        _apply_yaml_overrides(yaml_config.get(self.name))

        # 3) Command-line overrides applied last
        if meson_options_cmd_line_overrides is not None:
            from data_structures import DictUtils  # local import to avoid cycles

            cmd_overrides_dict = DictUtils.create_dict(meson_options_cmd_line_overrides)
            self.meson.override_meson_options_from_dict(cmd_overrides_dict)

        if diag_attributes_cmd_line_overrides:
            self.meson.override_meson_options_from_dict(
                {"diag_attribute_overrides": diag_attributes_cmd_line_overrides}
            )

        if diag_custom_defines_cmd_line_overrides:
            self.meson.override_meson_options_from_dict(
                {"diag_custom_defines": list(diag_custom_defines_cmd_line_overrides)}
            )

        if self.target == "spike":
            num_active_cpus = 1
            active_cpu_mask = self.diag_source.get_attribute_value("active_cpu_mask")
            if active_cpu_mask is not None:
                num_active_cpus = convert_cpu_mask_to_num_active_cpus(active_cpu_mask)

            # get the active_cpu_mask from the meson diag_attribute_overrides
            for diag_attribute in self.meson.get_meson_options().get(
                "diag_attribute_overrides", []
            ):
                if diag_attribute.startswith("active_cpu_mask="):
                    active_cpu_mask = diag_attribute.split("=", 1)[1]
                    num_active_cpus = convert_cpu_mask_to_num_active_cpus(active_cpu_mask)

            spike_overrides = {
                "spike_additional_arguments": [
                    f"-p{num_active_cpus}",
                ],
            }

            self.meson.override_meson_options_from_dict(spike_overrides)

    # ---------------------------------------------------------------------
    # Status label helpers (moved/centralized color logic)
    # ---------------------------------------------------------------------
    def _fmt_duration(self, seconds: Optional[float]) -> str:
        try:
            return f" ({seconds:.2f}s)" if seconds is not None else ""
        except Exception:
            return ""

    def _colorize_status_prefix(self, label: str) -> str:
        """Colorize a status label prefix, preserving any trailing text.

        Recognizes prefixes: PASS, CONDITIONAL_PASS, EXPECTED_FAIL, FAILED, PENDING.
        """
        # Order matters: check longer prefixes first
        mapping = {
            "CONDITIONAL_PASS": ("\u001b[33m", len("CONDITIONAL_PASS")),  # yellow
            "EXPECTED_FAIL": ("\u001b[33m", len("EXPECTED_FAIL")),  # yellow
            "PASS": ("\u001b[32m", len("PASS")),  # green
            "FAILED": ("\u001b[31m", len("FAILED")),  # red
            "PENDING": ("\u001b[33m", len("PENDING")),  # yellow
        }
        for prefix, (color, plen) in mapping.items():
            if label.startswith(prefix):
                reset = "\u001b[0m"
                return f"{color}{prefix}{reset}" + label[plen:]
        return label

    def colorize_status_text(self, text: str) -> str:
        """Public helper to colorize a status-bearing string by prefix only.

        Safe to pass padded strings; only the leading status token is colorized.
        """
        return self._colorize_status_prefix(text or "")

    def format_build_label(self, include_duration: bool = False, color: bool = False) -> str:
        base = self.compile_state.name
        if include_duration:
            base += self._fmt_duration(self.compile_duration_s)
        return self._colorize_status_prefix(base) if color else base

    def format_run_label(self, include_duration: bool = False, color: bool = False) -> str:
        base = self.run_state.name
        if include_duration:
            base += self._fmt_duration(self.run_duration_s)
        return self._colorize_status_prefix(base) if color else base

    def compile(self):
        start_time = time.perf_counter()
        if self.meson is None:
            self.compile_error = f"Meson object does not exist for diag: {self.name}"
            self.compile_duration_s = time.perf_counter() - start_time
            self.compile_state = self.CompileState.FAILED
            return

        try:
            self.meson.setup()
            compiled_assets = self.meson.compile()
            for asset_type, asset_path in compiled_assets.items():
                self.add_build_asset(asset_type, asset_path)
            self.compile_error = None
            self.current_state = self.state.COMPILED
            self.compile_state = self.CompileState.PASS
        except Exception as exc:
            self.compile_error = str(exc)
            self.compile_state = self.CompileState.FAILED
        finally:
            self.compile_duration_s = time.perf_counter() - start_time

    def run(self):
        start_time = time.perf_counter()
        if self.meson is None:
            self.run_error = f"Meson object does not exist for diag: {self.name}"
            self.run_duration_s = time.perf_counter() - start_time
            self.run_state = self.RunState.FAILED
            return
        if self.compile_state != self.CompileState.PASS:
            # Do not run if compile failed
            return

        try:
            run_assets = self.meson.test()
            for asset_type, asset_path in run_assets.items():
                self.add_build_asset(asset_type, asset_path)
            self.run_error = None
            self.run_return_code = 0
            self.current_state = self.state.RUN
            self.run_state = self.RunState.PASS
        except Exception as exc:
            # Capture return code for MesonBuildError to allow expected-fail handling
            try:
                if isinstance(exc, MesonBuildError):
                    self.run_return_code = exc.return_code
            except Exception:
                pass
            self.run_error = str(exc)
        finally:
            self.run_duration_s = time.perf_counter() - start_time
            # Normalize run_state based on expected_fail, return code, and error
            try:
                if self.expected_fail is True:
                    # Expected to fail:
                    if self.run_return_code is not None and self.run_return_code != 0:
                        # This is the expected behavior
                        self.run_state = self.RunState.EXPECTED_FAIL
                        self.run_error = None
                    elif self.run_return_code == 0:
                        # Unexpected pass
                        self.run_state = self.RunState.FAILED
                        self.run_error = "Diag run passed but was expected to fail."
                    else:
                        # No return code; treat as failure unless error text indicates otherwise
                        self.run_state = (
                            self.RunState.EXPECTED_FAIL
                            if self.run_error is None
                            else self.RunState.FAILED
                        )
                else:
                    # Not expected to fail:
                    if self.run_error is None and (
                        self.run_return_code is None or self.run_return_code == 0
                    ):
                        self.run_state = self.RunState.PASS
                    else:
                        self.run_state = self.RunState.FAILED
            except Exception:
                # Conservative fallback
                if self.run_error is not None:
                    self.run_state = self.RunState.FAILED
                # else keep whatever was set earlier

    def generate_padded_binary(self) -> Optional[str]:
        """
        Generate a 4-byte aligned binary from the ELF build asset and register it
        as the 'padded_binary' build asset. Returns the path to the generated
        binary, or None on failure.
        """
        # If already generated and present on disk, return it directly
        try:
            existing = self.build_assets.get("padded_binary")
            if existing and os.path.exists(existing):
                return existing
        except Exception:
            pass

        # Ensure ELF asset exists
        try:
            elf_path = self.get_build_asset("elf")
        except Exception as exc:
            log.error(f"ELF asset not available for {self.name}: {exc}")
            return None

        try:
            gen_path = generate_padded_binary_from_elf(
                elf_path=elf_path,
                output_dir_path=self.build_dir,
                name_for_logs=self.name,
            )
            if gen_path is None:
                return None

            # Register the asset without copying (it's already in build_dir)
            try:
                # Remove stale registration if present
                if "padded_binary" in self.build_assets:
                    self.build_assets.pop("padded_binary", None)
                self.add_build_asset(
                    "padded_binary",
                    str(gen_path),
                    asset_action=AssetAction.NO_COPY,
                )
            except Exception as exc:
                # If registration fails for a non-existent file, treat as failure
                if not os.path.exists(gen_path):
                    log.error(f"Failed to register padded_binary for {self.name}: {exc}")
                    return None
                # Otherwise continue and return the path

            return str(gen_path)
        except Exception as exc:
            log.error(f"Failed to generate padded binary for {self.name}: {exc}")
            return None

    def apply_batch_outcome_from_junit_status(self, junit_status: Optional[str]) -> None:
        """Apply batch-run outcome to this unit using a junit testcase status string.

        junit_status: one of "pass", "fail", "skipped".
        """
        # Default pessimistic state
        self.run_state = self.RunState.FAILED
        if junit_status == "fail":
            # truf marks fail when rc==0 for expected_fail=True, or rc!=0 for expected_fail=False
            if self.expected_fail:
                self.run_return_code = 0
                self.run_error = "Diag run passed but was expected to fail."
                self.run_state = self.RunState.FAILED
            else:
                self.run_return_code = 1
                self.run_error = "Batch run failure"
                self.run_state = self.RunState.FAILED
        elif junit_status == "pass" or junit_status == "conditional_pass":
            # truf marks pass when rc!=0 for expected_fail=True, or rc==0 for expected_fail=False
            if self.expected_fail:
                self.run_return_code = 1
                self.run_error = None
                self.run_state = self.RunState.EXPECTED_FAIL
            else:
                self.run_return_code = 0
                self.run_error = None
                if junit_status == "conditional_pass":
                    self.run_state = self.RunState.CONDITIONAL_PASS
                else:
                    self.run_state = self.RunState.PASS
        else:
            # If not in report or unknown status, assume failure conservatively
            self.run_return_code = 1
            self.run_error = "No batch result"
            self.run_state = self.RunState.FAILED

    def mark_no_junit_report(self) -> None:
        self.run_error = "No JUnit report"
        self.run_return_code = None
        self.run_state = self.RunState.FAILED

    def mark_batch_exception(self, exc: Exception) -> None:
        try:
            self.run_error = f"{type(exc).__name__}: {exc}"
        except Exception:
            self.run_error = "Batch run failed with an exception"
        self.run_return_code = None
        self.run_state = self.RunState.FAILED

    def __str__(self) -> str:
        current_buildtype = self.meson.get_meson_options().get("buildtype", "release")

        compile_label = self.compile_state.name
        if self.compile_error:
            compile_label += f": {self.compile_error}"

        run_label = self.run_state.name
        if self.run_error:
            run_label += f": {self.run_error}"

        compile_colored = self.colorize_status_text(compile_label)
        run_colored = self.colorize_status_text(run_label)

        print_string = (
            f"\n\tName: {self.name}"
            f"\n\tDirectory: {self.build_dir}"
            f"\n\tBuildType: {current_buildtype},"
            f"\n\tTarget: {self.target},"
            f"\n\tBootConfig: {self.boot_config},"
            f"\n\tCompile: {compile_colored},"
            f"\n\tRun: {run_colored}"
        )
        print_string += f"\n\tRNG Seed: {hex(self.rng_seed)}"
        print_string += f"\n\tSource Info:\n{self.diag_source}"
        print_string += "\n\tMeson Options:\n" + self.meson.get_meson_options_pretty(spacing="\t\t")
        print_string += f"\n\tAssets: {self.build_assets}"

        return print_string

    def add_build_asset(
        self,
        build_asset_type,
        build_asset_src_file_path,
        build_asset_file_name=None,
        asset_action=AssetAction.COPY,
    ):
        if not isinstance(asset_action, AssetAction):
            raise TypeError("asset_action must be an instance of AssetAction Enum")

        if build_asset_type in self.build_assets:
            raise Exception(f"Asset already exists: {build_asset_type}")

        if build_asset_file_name is None:
            build_asset_file_name = os.path.basename(os.path.normpath(build_asset_src_file_path))

        if not os.path.exists(build_asset_src_file_path):
            raise Exception(f"Asset does not exist: {build_asset_src_file_path}")

        if asset_action == AssetAction.NO_COPY:
            self.build_assets[build_asset_type] = build_asset_src_file_path
        elif asset_action == AssetAction.MOVE:
            self.build_assets[build_asset_type] = shutil.move(
                build_asset_src_file_path, f"{self.build_dir}/{build_asset_file_name}"
            )
        elif asset_action == AssetAction.COPY:
            self.build_assets[build_asset_type] = shutil.copy(
                build_asset_src_file_path, f"{self.build_dir}/{build_asset_file_name}"
            )
        else:
            raise Exception(f"Invalid Asset action type: {asset_action}")

    def get_build_asset(self, build_asset_type):
        if build_asset_type not in self.build_assets:
            raise Exception(f"Asset {build_asset_type} does not exist")

        return self.build_assets[build_asset_type]

    def get_build_directory(self):
        return self.build_dir

    def get_name(self):
        return self.name
