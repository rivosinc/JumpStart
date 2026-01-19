# SPDX-FileCopyrightText: 2023 - 2026 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
System utility functions for process management and file operations.

This module includes an automatic process cleanup mechanism that ensures spawned
subprocesses (like Spike) are killed when the script is interrupted (Ctrl+C) or exits.

Process Cleanup Mechanism:
--------------------------
1. All processes spawned via run_command() are tracked in a global registry
2. A SIGINT (Ctrl+C) handler is installed at module import time
3. When Ctrl+C is pressed:
   - The signal handler immediately kills all registered process groups
   - The original Python signal handler is called to raise KeyboardInterrupt
   - This ensures single Ctrl+C kills all Spike processes across all threads
4. An atexit handler provides backup cleanup on normal script exit
"""

import atexit
import logging as log
import os
import shutil
import signal
import subprocess
import threading
import time

# Global registry to track active process groups so they can be cleaned up on interrupt
_active_process_groups = set()
_process_groups_lock = threading.Lock()
_original_sigint_handler = signal.getsignal(signal.SIGINT)
_cleanup_in_progress = False


def register_process_group(pgid):
    """Register a process group ID for cleanup on interrupt."""
    with _process_groups_lock:
        _active_process_groups.add(pgid)
        log.debug(f"Registered process group: {pgid}")


def unregister_process_group(pgid):
    """Unregister a process group ID."""
    with _process_groups_lock:
        _active_process_groups.discard(pgid)
        log.debug(f"Unregistered process group: {pgid}")


def cleanup_all_process_groups(show_message=True):
    """Kill all registered process groups. Called on script interruption or exit.

    This function is idempotent and safe to call multiple times.
    """
    global _cleanup_in_progress

    with _process_groups_lock:
        # Prevent concurrent cleanup attempts
        if _cleanup_in_progress or not _active_process_groups:
            return

        _cleanup_in_progress = True
        process_groups = list(_active_process_groups)

    # Only print if we have processes to clean up and message is requested
    if show_message:
        try:
            log.info("Cleaning up spawned processes...")
        except Exception:
            # Logging might not be available during shutdown
            try:
                print("\nCleaning up spawned processes...", flush=True)
            except Exception:
                pass

    # First pass: send SIGTERM to all process groups
    for pgid in process_groups:
        try:
            os.killpg(pgid, signal.SIGTERM)
            try:
                log.debug(f"Sent SIGTERM to process group: {pgid}")
            except Exception:
                pass
        except ProcessLookupError:
            # Process already terminated
            pass
        except Exception as e:
            try:
                log.warning(f"Failed to kill process group {pgid}: {e}")
            except Exception:
                pass

    # Give processes a brief moment to terminate gracefully
    if process_groups:
        time.sleep(0.05)

    # Clear the registry
    with _process_groups_lock:
        _active_process_groups.clear()
        _cleanup_in_progress = False


def _sigint_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) by immediately killing all spawned processes."""
    # First, kill all spawned processes immediately
    cleanup_all_process_groups(show_message=True)

    # Then restore and call the original handler to raise KeyboardInterrupt
    signal.signal(signal.SIGINT, _original_sigint_handler)
    if callable(_original_sigint_handler):
        _original_sigint_handler(signum, frame)
    else:
        # If no handler or default, raise KeyboardInterrupt
        raise KeyboardInterrupt()


# Install our signal handler at import time.
signal.signal(signal.SIGINT, _sigint_handler)

# Register cleanup function to run at exit (backup)
atexit.register(lambda: cleanup_all_process_groups(show_message=False))


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


def read_io_stream(stream, callback):
    for line in iter(stream.readline, b""):
        callback(line)


def run_command(command, run_directory, timeout=None, extra_env=None):
    log.debug(f"Running command: {' '.join(command)}")
    group_pid = None
    returncode = None
    stdout_output = []
    stderr_output = []
    # Prepare environment
    env = os.environ.copy()
    if extra_env is not None:
        env.update(extra_env)
    try:
        p = subprocess.Popen(
            command,
            cwd=run_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,  # Assign the child and all its subprocesses to a new process group.
            env=env,
        )
        group_pid = os.getpgid(p.pid)
        register_process_group(group_pid)

        # Function to capture output
        def capture_output(stream, log_func, output_list):
            for line in iter(stream.readline, b""):
                decoded_line = line.decode().strip()
                log_func(decoded_line)
                output_list.append(decoded_line)

        # Print stdout and stderr in real-time as they are produced
        stdout_thread = threading.Thread(
            target=capture_output, args=(p.stdout, lambda x: log.debug(x), stdout_output)
        )
        stderr_thread = threading.Thread(
            target=capture_output, args=(p.stderr, lambda x: log.debug(x), stderr_output)
        )
        stdout_thread.start()
        stderr_thread.start()

        try:
            returncode = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            log.warning(f"Command timed out after {timeout}s, killing process group {group_pid}")
            try:
                os.killpg(group_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass  # Process already terminated
            returncode = -1

        if returncode != 0:
            log.error(f"COMMAND FAILED: {' '.join(command)}")
            full_output = f"STDOUT:\n{'-' * 40}\n"
            full_output += "\n".join(stdout_output)
            full_output += f"\n\nSTDERR:\n{'-' * 40}\n"
            full_output += "\n".join(stderr_output)
            log.error(full_output)
        else:
            log.debug("Command executed successfully.")

        stdout_thread.join()
        stderr_thread.join()

    except KeyboardInterrupt:
        log.error(f"Command: {' '.join(command)} interrupted.")
        # Note: cleanup_all_process_groups() is already called by the signal handler,
        # but we call it here as a safety net in case the signal handler didn't run.
        # The function is idempotent, so calling it multiple times is safe.
        cleanup_all_process_groups(show_message=False)
        raise Exception(f"Command: {' '.join(command)} interrupted.")
    finally:
        # Always unregister the process group when done
        if group_pid is not None:
            unregister_process_group(group_pid)

    return returncode
