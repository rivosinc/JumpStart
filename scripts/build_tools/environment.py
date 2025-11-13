# SPDX-FileCopyrightText: 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Dict, List, Optional

import yaml


class Environment:
    """Represents a build environment with configuration attributes."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.run_target = kwargs.get("run_target")
        self.override_meson_options = kwargs.get("override_meson_options", {})
        self.override_diag_attributes = kwargs.get("override_diag_attributes", [])
        self.extends = kwargs.get("extends")  # String or list of strings
        self.hidden = kwargs.get(
            "hidden", False
        )  # Whether this environment should be hidden from lists

    def __str__(self) -> str:
        return (
            f"Environment(name={self.name}, run_target={self.run_target}, extends={self.extends})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class EnvironmentManager:
    """Manages environment configurations with inheritance support."""

    def __init__(self):
        self.environments: Dict[str, Environment] = {}

    def register_environment(self, env: Environment) -> None:
        """Register an environment with the manager."""
        self.environments[env.name] = env

    def get_environment(self, name: str) -> Environment:
        """Get a fully resolved environment with all inherited attributes merged."""
        return self._resolve_environment(name)

    def list_environments(self) -> Dict[str, Environment]:
        """Get all registered environments (unresolved)."""
        return self.environments.copy()

    def list_visible_environments(self) -> Dict[str, Environment]:
        """Get all visible (non-hidden) registered environments (unresolved)."""
        return {name: env for name, env in self.environments.items() if not env.hidden}

    def _resolve_environment(self, name: str, visited: Optional[set] = None) -> Environment:
        """Recursively resolve inheritance chain and merge attributes."""
        if visited is None:
            visited = set()

        if name in visited:
            raise ValueError(f"Circular inheritance detected: {name}")

        if name not in self.environments:
            raise ValueError(f"Environment '{name}' not found")

        env = self.environments[name]
        visited.add(name)

        # If no inheritance, return as-is
        if not env.extends:
            return env

        # Handle single inheritance
        if isinstance(env.extends, str):
            parent = self._resolve_environment(env.extends, visited)
            return self._merge_environments(parent, env)

        # # Handle multiple inheritance
        # elif isinstance(env.extends, list):
        #     # Merge all parents first
        #     merged_parent = None
        #     for parent_name in env.extends:
        #         parent = self._resolve_environment(parent_name, visited)
        #         if merged_parent is None:
        #             merged_parent = parent
        #         else:
        #             merged_parent = self._merge_environments(merged_parent, parent)

        #     # Then merge with current environment
        #     return self._merge_environments(merged_parent, env)

        else:
            raise ValueError(f"Invalid extends value for environment '{name}': {env.extends}")

    def _merge_environments(self, parent: Environment, child: Environment) -> Environment:
        """Merge parent and child environments, with child taking precedence."""
        merged = Environment(child.name)

        # Merge run_target (child overrides parent)
        merged.run_target = child.run_target if child.run_target is not None else parent.run_target

        # Merge meson options (child overrides parent)
        merged.override_meson_options = parent.override_meson_options.copy()
        merged.override_meson_options.update(child.override_meson_options)

        # Merge diag attributes (child overrides parent, not append)
        # This prevents duplication when the same attribute is defined in both parent and child
        merged.override_diag_attributes = parent.override_diag_attributes.copy()

        # Add child attributes, but avoid duplicates
        for attr in child.override_diag_attributes:
            # Check if this attribute (key part) already exists
            attr_key = attr.split("=")[0] if "=" in attr else attr
            existing_keys = [
                a.split("=")[0] if "=" in a else a for a in merged.override_diag_attributes
            ]

            if attr_key in existing_keys:
                # Replace the existing attribute
                for i, existing_attr in enumerate(merged.override_diag_attributes):
                    existing_key = (
                        existing_attr.split("=")[0] if "=" in existing_attr else existing_attr
                    )
                    if existing_key == attr_key:
                        merged.override_diag_attributes[i] = attr
                        break
            else:
                # Add new attribute
                merged.override_diag_attributes.append(attr)

        return merged

    def load_from_yaml(self, yaml_content: str) -> None:
        """Load environments from YAML content."""
        data = yaml.safe_load(yaml_content)
        if not data or "environments" not in data:
            raise ValueError("YAML content must contain an 'environments' section")

        for env_name, env_config in data["environments"].items():
            if not isinstance(env_config, dict):
                raise ValueError(f"Environment '{env_name}' configuration must be a dictionary")

            env = Environment(env_name, **env_config)
            self.register_environment(env)

    def load_from_file(self, file_path: str) -> None:
        """Load environments from a YAML file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Environment file not found: {file_path}")

        with open(file_path) as f:
            yaml_content = f.read()

        self.load_from_yaml(yaml_content)

    def get_inheritance_chain(self, name: str) -> List[str]:
        """Get the inheritance chain for an environment (for debugging/display)."""
        chain = []
        visited = set()

        def _build_chain(env_name: str):
            if env_name in visited:
                return
            visited.add(env_name)

            if env_name not in self.environments:
                return

            env = self.environments[env_name]
            if env.extends:
                if isinstance(env.extends, str):
                    _build_chain(env.extends)
                elif isinstance(env.extends, list):
                    for parent in env.extends:
                        _build_chain(parent)

            chain.append(env_name)

        _build_chain(name)
        return chain


def get_environment_manager() -> EnvironmentManager:
    """Create the default environment manager by loading from environments.yaml."""
    manager = EnvironmentManager()

    # Load from the environments.yaml file in the same directory as this script
    env_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "environments.yaml")

    manager.load_from_file(env_file_path)
    return manager


def format_environment_list(manager: EnvironmentManager) -> str:
    """Format a list of all visible environments for display."""
    output = ["Available environments:", "=" * 50]

    for env_name in sorted(manager.list_visible_environments().keys()):
        try:
            resolved_env = manager.get_environment(env_name)
            inheritance_chain = manager.get_inheritance_chain(env_name)

            output.append(f"\n{env_name}:")
            output.append(f"  Run Target: {resolved_env.run_target}")

            if len(inheritance_chain) > 1:
                chain_str = " -> ".join(inheritance_chain[:-1])  # Exclude self
                output.append(f"  Inheritance: {chain_str}")

            if resolved_env.override_meson_options:
                output.append("  Meson Options:")
                for key, value in resolved_env.override_meson_options.items():
                    output.append(f"    {key}: {value}")

            if resolved_env.override_diag_attributes:
                output.append("  Diag Attributes:")
                for attr in resolved_env.override_diag_attributes:
                    output.append(f"    {attr}")

        except Exception as e:
            output.append(f"\n{env_name}: ERROR - {e}")

    return "\n".join(output)
