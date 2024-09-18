# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import os
import shutil
import sys

import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from system import functions as system_functions  # noqa


class DiagSource:
    source_file_extensions = [".c", ".S"]
    diag_attribute_yaml_extensions = [
        ".diag_attributes.yaml",
        ".diag_attributes.yml",
    ]
    meson_options_override_yaml_extensions = ["meson_option_overrides.yaml"]

    def __init__(self, diag_src_dir) -> None:
        self.diag_src_dir = os.path.abspath(diag_src_dir)
        if not os.path.exists(self.diag_src_dir):
            raise Exception(f"Diag source directory does not exist: {self.diag_src_dir}")

        self.diag_sources = system_functions.find_files_with_extensions_in_dir(
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

        self.meson_options_override_yaml = system_functions.find_files_with_extensions_in_dir(
            self.diag_src_dir, self.meson_options_override_yaml_extensions
        )
        if len(self.meson_options_override_yaml) > 1:
            raise Exception(
                f"Found multiple meson options files: {self.meson_options_override_yaml}"
            )
        elif len(self.meson_options_override_yaml) == 1:
            self.meson_options_override_yaml = self.meson_options_override_yaml[0]
        else:
            self.meson_options_override_yaml = None

        self.diag_name = os.path.basename(os.path.normpath(self.diag_src_dir))

        self.active_hart_mask = None
        with open(self.get_diag_attributes_yaml()) as f:
            diag_attributes = yaml.safe_load(f)
            if "active_hart_mask" in diag_attributes:
                log.debug(
                    f"Found active_hart_mask specified by diag: {diag_attributes['active_hart_mask']}"
                )
                self.active_hart_mask = diag_attributes["active_hart_mask"]

    def __str__(self) -> str:
        return f"\t\tDiag: {self.diag_name}, Source Path: {self.diag_src_dir}\n\t\tSources: {self.diag_sources}\n\t\tAttributes: {self.diag_attributes_yaml}\n\t\tMeson options overrides file: {self.meson_options_override_yaml}"

    def get_name(self):
        return self.diag_name

    def get_diag_src_dir(self):
        return self.diag_src_dir

    def get_sources(self):
        return self.diag_sources

    def get_diag_attributes_yaml(self):
        return self.diag_attributes_yaml

    def get_meson_options_override_yaml(self):
        return self.meson_options_override_yaml

    def is_valid_source_directory(diag_src_dir):
        # if we can successfully make an object without taking an
        # exception then we have a valid diag source directory.
        try:
            DiagSource(diag_src_dir)
        except Exception:
            return False

        return True


class AssetAction(enum.IntEnum):
    MOVE = 0
    COPY = 1
    NO_COPY = 2


class DiagBuildTarget:
    supported_targets = ["qemu", "spike"]
    supported_toolchains = ["gcc", "llvm"]
    supported_boot_configs = ["fw-none"]

    def __init__(
        self,
        diag_src_dir,
        build_dir,
        buildtype,
        target,
        toolchain,
        boot_config,
        rng_seed,
        active_hart_mask_override,
        meson_options_cmd_line_overrides,
        diag_attributes_cmd_line_overrides,
    ) -> None:
        self.build_dir = os.path.abspath(build_dir)
        self.build_assets = {}
        self.diag_source = DiagSource(diag_src_dir)

        self.buildtype = buildtype
        assert target in self.supported_targets
        self.target = target
        self.rng_seed = rng_seed

        assert toolchain in self.supported_toolchains
        self.toolchain = toolchain

        assert boot_config in self.supported_boot_configs
        self.boot_config = boot_config

        self.active_hart_mask_override = active_hart_mask_override

        self.meson_options_cmd_line_overrides = meson_options_cmd_line_overrides

        self.diag_attributes_cmd_line_overrides = diag_attributes_cmd_line_overrides

    def __str__(self) -> str:
        print_string = f"\n\tName: {self.diag_source.diag_name}\n\tDirectory: {self.build_dir}\n\tAssets: {self.build_assets}\n\tBuildType: {self.buildtype},\n\tTarget: {self.target},\n\tBootConfig: {self.boot_config},"
        if self.rng_seed is not None:
            print_string += f"\n\tRNG Seed: {self.rng_seed}"
        print_string += f"\n\tSource Info:\n{self.diag_source}"

        return print_string

    def add_build_asset(
        self,
        build_asset_type,
        build_asset_src_file_path,
        build_asset_file_name=None,
        asset_action=AssetAction.MOVE,
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
        return self.diag_source.diag_name
