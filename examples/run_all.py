"""Run every Python example and report a concise summary."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="show output from each example",
    )
    arguments = parser.parse_args()

    examples_directory = Path(__file__).resolve().parent
    scripts = sorted(
        path
        for path in examples_directory.glob("*.py")
        if path.name != Path(__file__).name
    )
    failures = []

    with tempfile.TemporaryDirectory(prefix="demetrapy-examples-") as directory:
        for position, script in enumerate(scripts, start=1):
            print(
                f"[{position}/{len(scripts)}] {script.name} ... ",
                end="",
                flush=True,
            )
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=directory,
                capture_output=not arguments.show_output,
                text=True,
                check=False,
            )
            if completed.returncode == 0:
                print("ok")
                continue

            print("failed")
            failures.append(script.name)
            if completed.stdout:
                print(completed.stdout.rstrip())
            if completed.stderr:
                print(completed.stderr.rstrip(), file=sys.stderr)

    if failures:
        print(f"\nFailed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"\nAll {len(scripts)} examples passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())