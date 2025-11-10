# SPDX-FileCopyrightText: 2023 - 2025 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging as log
import os
import shutil
import signal
import subprocess


def create_empty_directory(directory):
    if os.path.isfile(directory):
        log.debug(f"{directory} is a file. Removing it.")
        os.remove(directory)
    elif os.path.isdir(directory) is True and len(os.listdir(directory)) > 0:
        log.debug(f"{directory} is a non-empty directory. Removing it.")
        shutil.rmtree(directory)

    if os.path.isdir(directory) is False:
        log.debug(f"Creating directory: {directory}")
        os.makedirs(directory)


def find_files_with_extensions_in_dir(root, extensions):
    if not os.path.exists(root):
        raise Exception(f"Root directory does not exist: {root}")

    sources = [
        os.path.join(root, f)
        for f in os.listdir(root)
        if (os.path.isfile(os.path.join(root, f)) and f.endswith(tuple(extensions)))
    ]
    return sources


def run_command(command, run_directory):
    log.debug(f"Running command: {' '.join(command)}")
    group_pid = None
    returncode = None

    try:
        p = subprocess.Popen(
            command,
            cwd=run_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # Assign the child and all its subprocesses to a new process group.
            universal_newlines=True,  # Ensures output is returned as a string rather than bytes.
        )
        group_pid = os.getpgid(p.pid)

        # Print stdout and stderr in real-time as they are produced
        for stdout_line in iter(p.stdout.readline, ""):
            log.debug(stdout_line.strip())

        for stderr_line in iter(p.stderr.readline, ""):
            log.error(stderr_line.strip())

        returncode = p.wait()

        if returncode != 0:
            log.error(f"COMMAND FAILED: {' '.join(command)}")
        else:
            log.debug("Command executed successfully.")

    except KeyboardInterrupt:
        log.error(f"Command: {' '.join(command)} interrupted.")
        if group_pid is not None:
            # p.kill() seems to only kill the child process and not the
            # subprocesses of the child. This leaves the subprocesses of the
            # child orphaned.
            # For example, "meson test" spawns spike which doesn't get killed
            # when p.kill() is called on "meson test".
            # Instead, kill the whole process group containing the child process
            # and it's subprocesses.
            os.killpg(group_pid, signal.SIGTERM)
        raise Exception(f"Command: {' '.join(command)} interrupted.")

    return returncode
