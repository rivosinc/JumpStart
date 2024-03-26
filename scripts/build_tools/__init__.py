# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# __init__.py

from .diag import DiagBuildTarget, DiagSource
from .meson import build_jumpstart_diag

# PEP8 guideline:
# https://peps.python.org/pep-0008/#public-and-internal-interfaces
# To better support introspection, modules should explicitly declare
# the names in their public API using the __all__ attribute.

__all__ = [
    "DiagSource",
    "DiagBuildTarget",
    "build_jumpstart_diag",
]
