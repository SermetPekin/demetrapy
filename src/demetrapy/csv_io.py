"""File-based seasonal adjustment helpers."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any, Callable, Sequence, TextIO

from .config import AdjustmentConfig, FREQUENCIES
from .engine import AdjustmentResult, adjust


PERIODS_PER_YEAR = dict(zip(FREQUENCIES, (12, 4, 2, 1)))


def adjust_csv(
    path: str | Path,
    *,
    config: str | Path | AdjustmentConfig | None = None,
    output: str | Path | None = None,
    detailed: bool = False,
    **overrides: Any,
) -> AdjustmentResult:
    """Adjust one CSV value column and optionally write compact results."""
    resolved = _resolve_config(config, overrides)
    dates, result = _process_csv(Path(path), resolved, detailed=detailed)
    if output is not None:
        with Path(output).open("w", newline="", encoding="utf-8") as stream:
            _write_csv(stream, dates, result.to_compact_dict())
    return result


def _resolve_config(
    config: str | Path | AdjustmentConfig | None,
    overrides: dict[str, Any] | None = None,
) -> AdjustmentConfig:
    resolved = config if isinstance(config, AdjustmentConfig) else AdjustmentConfig.load(config)
    if overrides:
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