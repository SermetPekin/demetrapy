"""Structured audit records for file-based adjustment runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from time import perf_counter
from typing import Any, Sequence
from uuid import uuid4

from .config import AdjustmentConfig
from .engine import AdjustmentResult, JDEMETRA_VERSION, RESULT_SCHEMA_VERSION


AUDIT_SCHEMA_VERSION = 1


class AuditRecorder:
    def __init__(
        self,
        directory: str | Path,
        input_path: Path,
        output_path: Path | None,
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.run_id = str(uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.timer = perf_counter()
        self.input_path = input_path
        self.output_path = output_path

    def success(
        self,
        config: AdjustmentConfig,
        dates: Sequence[str],
        result: AdjustmentResult,
    ) -> Path:
        messages = [asdict(message) for message in result.messages]
        model = asdict(result.arima_model) if result.arima_model is not None else None
        record = self._base_record(config, "success")
        record.update(
            input={
                **record["input"],
                "rows": len(dates),
                "first_period": dates[0] if dates else None,
                "last_period": dates[-1] if dates else None,
            },
            result={
                "method": result.method,
                "specification": result.specification,
                "diagnostics": dict(result.diagnostics),
                "processing_messages": messages,
                "arima_model": model,
            },
            output=self._file_record(self.output_path),
            exception=None,
        )
        return self._write(record)

    def failure(
        self,
        error: Exception,
        config: AdjustmentConfig | None = None,
    ) -> Path:
        record = self._base_record(config, "failed")
        record.update(
            result=None,
            output=self._file_record(self.output_path),
            exception={
                "type": type(error).__name__,
                "message": str(error),
            },
        )
        return self._write(record)

    def _base_record(
        self,
        config: AdjustmentConfig | None,
        status: str,
    ) -> dict[str, Any]:
        finished_at = datetime.now(timezone.utc)
        config_values = config.to_dict() if config is not None else None
        return {
            "audit_schema_version": AUDIT_SCHEMA_VERSION,
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "run_id": self.run_id,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(perf_counter() - self.timer, 6),
            "versions": _versions(),
            "input": self._file_record(self.input_path),
            "configuration": _redact_config(config_values),
            "configuration_sha256": _json_hash(config_values),
        }

    def _file_record(self, path: Path | None) -> dict[str, Any] | None:
        if path is None:
            return None
        record: dict[str, Any] = {"filename": path.name}
        if path.is_file():
            record.update(size_bytes=path.stat().st_size, sha256=_file_hash(path))
        else:
            record.update(size_bytes=None, sha256=None)
        return record

    def _write(self, record: dict[str, Any]) -> Path:
        timestamp = self.started_at.strftime("%Y%m%dT%H%M%S.%fZ")
        manifest_path = self.directory / f"{timestamp}_{self.run_id}.json"
        encoded = json.dumps(record, indent=2, sort_keys=True) + "\n"
        temporary = manifest_path.with_suffix(".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(manifest_path)

        line = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        descriptor = os.open(
            self.directory / "runs.jsonl",
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o644,
        )
        try:
            written = os.write(descriptor, line)
            if written != len(line):
                raise OSError("could not append the complete audit record")
        finally:
            os.close(descriptor)
        return manifest_path


def _versions() -> dict[str, str | None]:
    return {
        "demetrapy": _package_version("demetrapy"),
        "python": platform.python_version(),
        "jpype": _package_version("JPype1"),
        "java": _java_version(),
        "jdemetra": JDEMETRA_VERSION,
    }


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _java_version() -> str | None:
    try:
        import jpype

        if jpype.isJVMStarted():
            return str(jpype.JClass("java.lang.System").getProperty("java.version"))
    except Exception:
        return None
    return None


def _redact_config(values: dict[str, Any] | None) -> dict[str, Any] | None:
    if values is None:
        return None
    redacted = json.loads(json.dumps(values))
    for variable in redacted.get("user_variables", []):
        if "values" not in variable:
            continue
        original = variable["values"]
        variable["values"] = {
            "redacted": True,
            "count": len(original) if hasattr(original, "__len__") else None,
            "sha256": _json_hash(original),
        }
    return redacted


def _json_hash(value: Any) -> str | None:
    if value is None:
        return None
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()