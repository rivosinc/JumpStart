#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import json
import sys

import yaml


def load_manifest_json(file_path):
    with open(file_path) as file:
        data = json.load(file)
    return data


manifest = {"payload": []}

for test_manifest_file in sys.argv[1:]:
    truf_test_manifest = load_manifest_json(test_manifest_file)
    if truf_test_manifest:
        manifest["payload"].append(truf_test_manifest)

yaml_str = yaml.dump(manifest, default_flow_style=False)
print(yaml_str)
