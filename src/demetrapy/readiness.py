"""Read-only environment checks for demetrapy."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
from typing import Callable, Sequence

from .engine import JAR_URL, JDEMETRA_VERSION


MINIMUM_PYTHON_VERSION = (3, 11)
MINIMUM_JAVA_VERSION = 9


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str
    action: str = ""


def run_readiness_checks(
    *,
    environment: dict[str, str] | None = None,
    java_executable: str | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[ReadinessCheck, ...]:
    """Inspect runtime prerequisites without starting Java or downloading files."""
    values = os.environ if environment is None else environment
    checks = [_python_check(), _jpype_check()]

    executable = java_executable or shutil.which("java", path=values.get("PATH"))
    java_architecture = None
    if executable is None:
        checks.append(
            ReadinessCheck(
                "Java",
                "ERROR",
                "java was not found on PATH",
                f"Install Java {MINIMUM_JAVA_VERSION} or later, add it to PATH, "
                "then run 'java -version'.",
            )
        )
    else:
        java_check, java_architecture = _java_check(executable, command_runner)
        checks.append(java_check)

    checks.append(_architecture_check(java_architecture))
    checks.append(_jar_check(values))
    return tuple(checks)


def is_ready(checks: Sequence[ReadinessCheck]) -> bool:
    return all(check.status != "ERROR" for check in checks)


def _python_check() -> ReadinessCheck:
    version = platform.python_version()
    bits = struct.calcsize("P") * 8
    minimum = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)
    if sys.version_info < MINIMUM_PYTHON_VERSION:
        return ReadinessCheck(
            "Python",
            "ERROR",
            f"{version} ({bits}-bit)",
            f"Install Python {minimum} or later, then recreate the virtual "
            f"environment (for example: 'uv venv --python {minimum}').",
        )
    return ReadinessCheck("Python", "OK", f"{version} ({bits}-bit)")


def _jpype_check() -> ReadinessCheck:
    try:
        version = importlib.metadata.version("JPype1")
    except importlib.metadata.PackageNotFoundError:
        return ReadinessCheck(
            "JPype",
            "ERROR",
            "not installed",
            "Run 'python -m pip install --upgrade JPype1 demetrapy'.",
        )
    return ReadinessCheck("JPype", "OK", version)


def _java_check(
    executable: str,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[ReadinessCheck, int | None]:
    try:
        completed = command_runner(
            [executable, "-XshowSettings:properties", "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return (
            ReadinessCheck(
                "Java",
                "ERROR",
                str(error),
                "Run 'java -version'. If it fails, reinstall Java and verify PATH/JAVA_HOME.",
            ),
            None,
        )

    output = f"{completed.stdout}\n{completed.stderr}"
    version = _java_property(output, "java.version") or _java_version(output)
    architecture_name = _java_property(output, "os.arch")
    architecture = _architecture_bits(architecture_name)
    if completed.returncode != 0:
        return (
            ReadinessCheck(
                "Java",
                "ERROR",
                f"command failed with exit code {completed.returncode}",
                "Run 'java -version'. If it fails, reinstall Java and verify PATH/JAVA_HOME.",
            ),
            architecture,
        )
    major = _java_major_version(version)
    if major is not None and major < MINIMUM_JAVA_VERSION:
        return (
            ReadinessCheck(
                "Java",
                "ERROR",
                f"{version} ({architecture_name or 'unknown architecture'})",
                f"Install Java {MINIMUM_JAVA_VERSION} or later, update "
                "PATH/JAVA_HOME, then run 'java -version'.",
            ),
            architecture,
        )
    return (
        ReadinessCheck(
            "Java",
            "OK",
            f"{version or 'version unknown'} ({architecture_name or 'architecture unknown'})",
        ),
        architecture,
    )


def _architecture_check(java_bits: int | None) -> ReadinessCheck:
    python_bits = struct.calcsize("P") * 8
    if java_bits is None:
        return ReadinessCheck(
            "Architecture",
            "WARNING",
            f"Python is {python_bits}-bit; Java architecture could not be determined",
            "Run 'java -XshowSettings:properties -version' and confirm os.arch "
            "matches Python.",
        )
    if java_bits != python_bits:
        return ReadinessCheck(
            "Architecture",
            "ERROR",
            f"Python is {python_bits}-bit; Java is {java_bits}-bit",
            "Install Python and Java builds for the same architecture, then "
            "recreate the virtual environment.",
        )
    return ReadinessCheck("Architecture", "OK", f"Python and Java are {python_bits}-bit")


def _jar_check(environment: dict[str, str]) -> ReadinessCheck:
    configured = environment.get("DEMETRAPY_JAR")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            return ReadinessCheck(
                "JDemetra+ JAR",
                "ERROR",
                f"DEMETRAPY_JAR does not point to a file: {path}",
                "Point DEMETRAPY_JAR to a readable JAR file, or unset it to "
                "enable the automatic download.",
            )
        return ReadinessCheck(
            "JDemetra+ JAR",
            "OK",
            f"{path} (configured override)",
        )

    path = Path.home() / ".cache" / "demetrapy" / Path(JAR_URL).name
    if path.is_file():
        return ReadinessCheck(
            "JDemetra+ JAR",
            "OK",
            f"{path} (version {JDEMETRA_VERSION})",
        )

    writable_parent = path.parent
    while not writable_parent.exists() and writable_parent != writable_parent.parent:
        writable_parent = writable_parent.parent
    if not writable_parent.is_dir() or not os.access(writable_parent, os.W_OK):
        return ReadinessCheck(
            "JDemetra+ JAR",
            "ERROR",
            f"cache is missing and {writable_parent} is not writable",
            "Set DEMETRAPY_JAR to a readable JAR or make the cache writable.",
        )
    return ReadinessCheck(
        "JDemetra+ JAR",
        "WARNING",
        f"not cached; version {JDEMETRA_VERSION} will download on first use",
        "For offline use, set DEMETRAPY_JAR to a local copy before processing.",
    )


def _java_property(output: str, name: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+)$", output, re.MULTILINE)
    return match.group(1).strip() if match else None


def _java_version(output: str) -> str | None:
    match = re.search(r'version\s+"([^"]+)"', output)
    return match.group(1) if match else None


def _java_major_version(version: str | None) -> int | None:
    if not version:
        return None
    parts = version.split(".")
    candidate = parts[1] if parts[0] == "1" and len(parts) > 1 else parts[0]
    match = re.match(r"\d+", candidate)
    return int(match.group()) if match else None


def _architecture_bits(name: str | None) -> int | None:
    if not name:
        return None
    normalized = name.lower()
    if "64" in normalized or normalized in {"aarch64", "s390x", "ppc64le"}:
        return 64
    if normalized in {"x86", "i386", "i486", "i586", "i686", "arm"}:
        return 32
    return None
