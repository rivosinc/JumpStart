# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import enum
import logging as log
import os
import random
import shutil
import sys

import yaml
from system import functions as system_functions  # noqa

from .meson import Meson  # noqa


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

        self.active_cpu_mask = None
        with open(self.get_diag_attributes_yaml()) as f:
            diag_attributes = yaml.safe_load(f)
            if "active_cpu_mask" in diag_attributes:
                log.debug(
                    f"Found active_cpu_mask specified by diag: {diag_attributes['active_cpu_mask']}"
                )
                self.active_cpu_mask = diag_attributes["active_cpu_mask"]

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
    supported_targets = ["spike"]
    supported_boot_configs = ["fw-none"]

    def __init__(
        self,
        diag_src_dir,
        build_dir,
        target,
        toolchain,
        buildtype,
        boot_config,
        rng_seed,
        jumpstart_dir,
        meson_options_cmd_line_overrides,
        diag_attributes_cmd_line_overrides,
        keep_meson_builddir,
    ) -> None:
        self.build_assets = {}
        self.diag_source = DiagSource(diag_src_dir)

        assert target in self.supported_targets
        self.target = target

        self.rng_seed = rng_seed
        if self.rng_seed is None:
            self.rng_seed = random.randrange(sys.maxsize)
        log.debug(
            f"DiagBuildTarget: {self.diag_source.diag_name} Seeding RNG with: {self.rng_seed}"
        )
        self.rng = random.Random(self.rng_seed)

        assert boot_config in self.supported_boot_configs
        self.boot_config = boot_config

        if self.target == "spike" and self.boot_config != "fw-none":
            raise Exception(
                f"Invalid boot_config {self.boot_config} for spike. Only fw-none is supported for spike."
            )

        diag_attributes_cmd_line_overrides = diag_attributes_cmd_line_overrides or []

        for override in diag_attributes_cmd_line_overrides:
            if override.startswith("active_cpu_mask="):
                override_value = override.split("=", 1)[1]
                if self.diag_source.active_cpu_mask is not None:
                    log.warning(
                        f"Overriding active_cpu_mask {self.diag_source.active_cpu_mask} with: {override_value}"
                    )
                self.diag_source.active_cpu_mask = override_value

        self.build_dir = os.path.abspath(build_dir)
        system_functions.create_empty_directory(self.build_dir)

        self.meson = Meson(
            toolchain,
            jumpstart_dir,
            self,
            keep_meson_builddir,
            buildtype,
            meson_options_cmd_line_overrides,
            diag_attributes_cmd_line_overrides,
        )

    def compile(self):
        if self.meson is None:
            raise Exception(f"Meson object does not exist for diag: {self.diag_source.diag_name}")

        self.meson.setup()

        compiled_assets = self.meson.compile()
        for asset_type, asset_path in compiled_assets.items():
            self.add_build_asset(asset_type, asset_path)

    def run(self):
        if self.meson is None:
            raise Exception(f"Meson object does not exist for diag: {self.diag_source.diag_name}")

        run_assets = self.meson.test()
        for asset_type, asset_path in run_assets.items():
            self.add_build_asset(asset_type, asset_path)

    def __str__(self) -> str:
        print_string = f"\n\tName: {self.diag_source.diag_name}\n\tDirectory: {self.build_dir}\n\tAssets: {self.build_assets}\n\tBuildType: {self.meson.buildtype},\n\tTarget: {self.target},\n\tBootConfig: {self.boot_config},"
        print_string += f"\n\tRNG Seed: {hex(self.rng_seed)}"
        print_string += f"\n\tSource Info:\n{self.diag_source}"

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
        return self.diag_source.diag_name
