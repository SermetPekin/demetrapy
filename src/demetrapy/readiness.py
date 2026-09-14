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
                "Install Java 8 or later and make the java command available.",
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
    if sys.version_info < (3, 9):
        return ReadinessCheck(
            "Python",
            "ERROR",
            f"{version} ({bits}-bit)",
            "Install Python 3.9 or later.",
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
            "Reinstall demetrapy to install its JPype1 dependency.",
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
                "Verify the Java installation and the java command on PATH.",
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
                "Run 'java -version' and repair the Java installation.",
            ),
            architecture,
        )
    major = _java_major_version(version)
    if major is not None and major < 8:
        return (
            ReadinessCheck(
                "Java",
                "ERROR",
                f"{version} ({architecture_name or 'unknown architecture'})",
                "Install Java 8 or later.",
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
            "Confirm Python and Java use the same architecture.",
        )
    if java_bits != python_bits:
        return ReadinessCheck(
            "Architecture",
            "ERROR",
            f"Python is {python_bits}-bit; Java is {java_bits}-bit",
            "Install matching Python and Java architectures.",
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
                "Correct DEMETRAPY_JAR or unset it to use the automatic cache.",
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