from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import Sequence, TextIO

from .config import AdjustmentConfig
from .engine import adjust

PERIODS_PER_YEAR = {"Monthly": 12, "Quarterly": 4, "HalfYearly": 2, "Yearly": 1}


def _read_csv(path: Path, config: AdjustmentConfig) -> tuple[list[str], list[float]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        required = {config.date_column, config.value_column}
        if not required.issubset(columns):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        dates: list[str] = []
        values: list[float] = []
        for row_number, row in enumerate(reader, start=2):
            dates.append(row[config.date_column])
            try:
                values.append(float(row[config.value_column]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid number on CSV row {row_number}") from error
    if not values:
        raise ValueError("CSV contains no observations")
    return dates, values


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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seasonal-pri",
        description="Seasonally adjust a regular CSV series with JDemetra+ core.",
    )
    parser.add_argument("input", type=Path, help="CSV containing date and value columns")
    parser.add_argument("-c", "--config", type=Path, help="JSON adjustment configuration")
    parser.add_argument("-o", "--output", type=Path, help="output CSV (default: stdout)")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = AdjustmentConfig.load(args.config)
        dates, values = _read_csv(args.input, config)
        start_year, start_period = _start(dates, config.frequency)
        result = adjust(
            values,
            start_year=start_year,
            start_period=start_period,
            **config.engine_options(),
        )
        if any(len(series) != len(dates) for series in result.values()):
            raise RuntimeError("JDemetra+ returned an unexpected output length")
        if args.output:
            with args.output.open("w", newline="", encoding="utf-8") as stream:
                _write_csv(stream, dates, result)
        else:
            _write_csv(sys.stdout, dates, result)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"seasonal-pri: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())