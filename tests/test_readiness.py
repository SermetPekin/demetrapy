import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy.readiness import ReadinessCheck, is_ready, run_readiness_checks


def java_result(*, architecture="aarch64", version="17.0.12", returncode=0):
    return subprocess.CompletedProcess(
        args=["java"],
        returncode=returncode,
        stdout="",
        stderr=(
            "Property settings:\n"
            f"    java.version = {version}\n"
            f"    os.arch = {architecture}\n"
            f'openjdk version "{version}"\n'
        ),
    )


class ReadinessTest(unittest.TestCase):
    def test_ready_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "demetra.jar"
            jar.write_bytes(b"jar")
            checks = run_readiness_checks(
                environment={"DEMETRAPY_JAR": str(jar)},
                java_executable="/usr/bin/java",
                command_runner=lambda *args, **kwargs: java_result(
                    architecture="aarch64" if struct.calcsize("P") == 8 else "x86"
                ),
            )

        self.assertTrue(is_ready(checks))
        self.assertTrue(all(check.status == "OK" for check in checks))

    @patch("demetrapy.readiness.shutil.which", return_value=None)
    def test_missing_java_and_invalid_jar_are_blocking(self, mock_which) -> None:
        checks = run_readiness_checks(
            environment={
                "PATH": os.defpath,
                "DEMETRAPY_JAR": "/missing/demetra.jar",
            }
        )

        self.assertFalse(is_ready(checks))
        errors = {check.name: check for check in checks if check.status == "ERROR"}
        self.assertIn("Java", errors)
        self.assertIn("JDemetra+ JAR", errors)
        mock_which.assert_called_once()

    def test_architecture_mismatch_is_blocking(self) -> None:
        python_bits = struct.calcsize("P") * 8
        java_architecture = "x86" if python_bits == 64 else "aarch64"
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "demetra.jar"
            jar.write_bytes(b"jar")
            checks = run_readiness_checks(
                environment={"DEMETRAPY_JAR": str(jar)},
                java_executable="java",
                command_runner=lambda *args, **kwargs: java_result(
                    architecture=java_architecture
                ),
            )

        architecture = next(check for check in checks if check.name == "Architecture")
        self.assertEqual(architecture.status, "ERROR")
        self.assertFalse(is_ready(checks))

    def test_warning_does_not_block_readiness(self) -> None:
        checks = (
            ReadinessCheck("Python", "OK", "3.11"),
            ReadinessCheck("JDemetra+ JAR", "WARNING", "not cached"),
        )

        self.assertTrue(is_ready(checks))


if __name__ == "__main__":
    unittest.main()