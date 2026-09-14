"""File-based seasonal adjustment helpers."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

from .audit import AuditRecorder
from .config import AdjustmentConfig, Config, FREQUENCIES, normalize_config
from .engine import AdjustmentResult, adjust


PERIODS_PER_YEAR = dict(zip(FREQUENCIES, (12, 4, 2, 1)))


def adjust_csv(
    path: str | Path,
    *,
    config: str | Path | Config | None = None,
    output: str | Path | None = None,
    audit: str | Path | None = None,
    detailed: bool = False,
    **overrides: Any,
) -> AdjustmentResult:
    """Adjust one CSV value column and optionally write compact results."""
    _, result = _execute_csv(
        Path(path),
        config=config,
        overrides=overrides,
        output=Path(output) if output is not None else None,
        audit=audit,
        detailed=detailed,
    )
    return result


def _execute_csv(
    path: Path,
    *,
    config: str | Path | Config | None = None,
    overrides: dict[str, Any] | None = None,
    output: Path | None = None,
    audit: str | Path | None = None,
    detailed: bool = False,
    adjustment_function: Callable[..., AdjustmentResult] | None = None,
) -> tuple[list[str], AdjustmentResult]:
    recorder = AuditRecorder(audit, path, output) if audit is not None else None
    resolved = None
    try:
        resolved = _resolve_config(config, overrides)
        dates, result = _process_csv(
            path,
            resolved,
            detailed=detailed,
            adjustment_function=adjustment_function,
        )
        if output is not None:
            with output.open("w", newline="", encoding="utf-8") as stream:
                _write_csv(stream, dates, result.to_compact_dict())
        if recorder is not None:
            recorder.success(resolved, dates, result)
        return dates, result
    except Exception as error:
        if recorder is not None:
            try:
                recorder.failure(error, resolved)
            except Exception as audit_error:
                add_note = getattr(error, "add_note", None)
                if add_note is not None:
                    add_note(f"audit record could not be written: {audit_error}")
        raise


def _resolve_config(
    config: str | Path | Config | None,
    overrides: dict[str, Any] | None = None,
) -> AdjustmentConfig:
    typed_config = config is not None and not isinstance(
        config, (str, Path, AdjustmentConfig)
    )
    resolved = (
        AdjustmentConfig.load(config)
        if config is None or isinstance(config, (str, Path))
        else normalize_config(config)
    )
    if overrides:
        if typed_config:
            conflicts = sorted(
                name
                for name, value in overrides.items()
                if not hasattr(resolved, name) or getattr(resolved, name) != value
            )
            if conflicts:
                raise ValueError(
                    "config conflicts with adjustment options: "
                    + ", ".join(conflicts)
                )
            return resolved
        try:
            resolved = replace(resolved, **overrides)
        except TypeError as error:
            raise ValueError(f"invalid config override: {error}") from error
    resolved.validate()
    return resolved


def _process_csv(
    path: Path,
    config: AdjustmentConfig,
    *,
    detailed: bool = False,
    adjustment_function: Callable[..., AdjustmentResult] | None = None,
) -> tuple[list[str], AdjustmentResult]:
    config.validate()
    dates, values, user_values = _read_csv(path, config)
    start_year, start_period = _start(dates, config.frequency)
    engine_options = config.engine_options(user_values)
    if detailed:
        engine_options["detailed"] = True
    adjustment_function = adjustment_function or adjust
    result = adjustment_function(
        values,
        start_year=start_year,
        start_period=start_period,
        **engine_options,
    )
    compact = result.to_compact_dict()
    if any(len(series) != len(dates) for series in compact.values()):
        raise RuntimeError("JDemetra+ returned an unexpected output length")
    return dates, result


def _read_csv(
    path: Path, config: AdjustmentConfig
) -> tuple[list[str], list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        variable_columns = config.user_variable_columns()
        required = {config.date_column, config.value_column, *variable_columns}
        if not required.issubset(columns):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        dates: list[str] = []
        values: list[float] = []
        user_values = {column: [] for column in variable_columns}
        for row_number, row in enumerate(reader, start=2):
            dates.append(row[config.date_column])
            try:
                values.append(float(row[config.value_column]))
                for column in variable_columns:
                    user_values[column].append(float(row[column]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid number on CSV row {row_number}") from error
    if not values:
        raise ValueError("CSV contains no observations")
    return dates, values, user_values


def _start(dates: Sequence[str], frequency: str) -> tuple[int, int]:
    try:
        first = date.fromisoformat(dates[0])
        periods = PERIODS_PER_YEAR[frequency]
    except (ValueError, KeyError) as error:
        raise ValueError(
            "the first date must be ISO YYYY-MM-DD and frequency must be "
            f"one of {', '.join(PERIODS_PER_YEAR)}"
        ) from error
    return first.year, ((first.month - 1) * periods // 12) + 1


def _write_csv(
    stream: TextIO, dates: Sequence[str], result: dict[str, list[float]]
) -> None:
    writer = csv.writer(stream)
    names = list(result)
    writer.writerow(["date", *names])
    writer.writerows(
        [current_date, *(result[name][index] for name in names)]
        for index, current_date in enumerate(dates)
    )