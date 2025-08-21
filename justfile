# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Provides targets to build and run the jumpstart unit tests for development
# and CI purposes.

# To build and run the unit tests with all possible configurations:
# just test-all

# To target a particular configuration:
# just --set num_test_processes {{num_test_processes}} test <TOOLCHAIN> <BUILDTYPE> <TARGET>
# Examples:
#   just --set num_test_processes {{num_test_processes}} test gcc release spike
#   just --set num_test_processes {{num_test_processes}} test gcc debug spike

# build and test targets can be run individually
# Examples:
#   just build gcc release spike
#   just test gcc release spike

# To limit the number of parallel test jobs pass --set num_test_processes <NUM>
# Example:
#   just --set num_test_processes 10 test-all

num_test_processes := "max"

default:
    @just test-all

setup compiler buildtype target:
    @# For fw-none boot_config, priv modes and diag attributes are empty (defaults)
    meson setup {{compiler}}-{{buildtype}}-{{target}}-public-fw-none.builddir --cross-file cross_compile/public/{{compiler}}_options.txt --cross-file cross_compile/{{compiler}}.txt --buildtype {{buildtype}} -Ddiag_target={{target}} -Dboot_config=fw-none -Drivos_internal_build=false

build compiler buildtype target: (setup compiler buildtype target)
    meson compile -C {{compiler}}-{{buildtype}}-{{target}}-public-fw-none.builddir

test compiler buildtype target: (build compiler buildtype target)
    @case {{num_test_processes}} in \
        max) \
            num_processes_option=""; \
            ;; \
        *) \
            num_processes_option="-j "{{num_test_processes}}""; \
            ;; \
    esac; \
    meson test -C {{compiler}}-{{buildtype}}-{{target}}-public-fw-none.builddir $num_processes_option

clean_internal compiler buildtype target:
    rm -rf {{compiler}}-{{buildtype}}-{{target}}-public-fw-none.builddir

build-all-spike-gcc:
    @just build gcc debug spike
    @just build gcc release spike

build-all-spike:
    @just build-all-spike-gcc

build-all:
    @just build-all-spike

build-all-gcc:
    @just build-all-spike-gcc

test-all-spike-gcc:
    @just --set num_test_processes {{num_test_processes}} test gcc debug spike
    @just --set num_test_processes {{num_test_processes}} test gcc release spike

test-all-spike:
    @just test-all-spike-gcc

test-all-public:
    @just --set num_test_processes {{num_test_processes}} test gcc debug spike
    @just --set num_test_processes {{num_test_processes}} test gcc release spike

test-all:
    @just test-all-spike

test-all-gcc:
    @just test-all-spike-gcc

clean:
    rm -rf *.builddir
