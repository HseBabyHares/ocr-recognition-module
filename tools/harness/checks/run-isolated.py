#!/usr/bin/env python3
"""Run one gate command in a process group with bounded cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import sys


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap the command process group."""
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:
        process.kill()
    process.wait()


def main() -> int:
    """Run the requested command or return 124 after a clean timeout."""
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print(
            "usage: run-isolated.py TIMEOUT -- COMMAND [ARG ...]",
            file=sys.stderr,
        )
        return 2
    try:
        timeout = float(sys.argv[1])
    except ValueError:
        print("timeout must be numeric", file=sys.stderr)
        return 2
    if timeout <= 0:
        print("timeout must be positive", file=sys.stderr)
        return 2

    process = subprocess.Popen(
        sys.argv[3:],
        start_new_session=os.name == "posix",
    )
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_tree(process)
        print(f"command timed out after {timeout:g}s", file=sys.stderr)
        return 124
    except BaseException:
        terminate_tree(process)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
