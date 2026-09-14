from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Sequence, TextIO

from .config import AdjustmentConfig
from .engine import adjust
from .plotting import plot_adjustment

PERIODS_PER_YEAR = {"Monthly": 12, "Quarterly": 4, "HalfYearly": 2, "Yearly": 1}


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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demetrapy",
        description="Seasonally adjust a regular CSV series with JDemetra+ core.",
    )
    parser.add_argument(
        "input", nargs="?", type=Path, help="CSV containing date and value columns"
    )
    parser.add_argument(
        "-d", "--data", type=Path, help="CSV data file (alternative to positional input)"
    )
    parser.add_argument("-c", "--config", type=Path, help="JSON adjustment configuration")
    parser.add_argument("-o", "--output", type=Path, help="output CSV (default: stdout)")
    parser.add_argument("--method", choices=("x13", "tramoseats"), help="processing method")
    parser.add_argument("--spec", help="JDemetra+ preset, such as RSA4 or RSAfull")
    parser.add_argument(
        "--frequency", choices=tuple(PERIODS_PER_YEAR), help="observation frequency"
    )
    parser.add_argument("--date-column", help="CSV date column")
    parser.add_argument("--value-column", help="CSV value column")
    parser.add_argument("--plot", action="store_true", help="display an overview plot")
    parser.add_argument("--plot-output", type=Path, help="save an overview plot as PNG")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.input and args.data:
            raise ValueError("provide the data file either positionally or with --data, not both")
        input_path = args.data or args.input
        if input_path is None:
            raise ValueError("a data file is required; use --data FILE or a positional path")
        config = AdjustmentConfig.load(args.config)
        overrides = {
            name: getattr(args, name)
            for name in ("method", "spec", "frequency", "date_column", "value_column")
            if getattr(args, name) is not None
        }
        if overrides:
            config = replace(config, **overrides)
        dates, values, user_values = _read_csv(input_path, config)
        start_year, start_period = _start(dates, config.frequency)
        wants_plot = args.plot or args.plot_output is not None
        engine_options = config.engine_options(user_values)
        if wants_plot:
            engine_options["detailed"] = True
        engine_result = adjust(
            values,
            start_year=start_year,
            start_period=start_period,
            **engine_options,
        )
        result = engine_result.to_compact_dict()
        if any(len(series) != len(dates) for series in result.values()):
            raise RuntimeError("JDemetra+ returned an unexpected output length")
        if args.output:
            with args.output.open("w", newline="", encoding="utf-8") as stream:
                _write_csv(stream, dates, result)
        else:
            _write_csv(sys.stdout, dates, result)
        if wants_plot:
            figure = plot_adjustment(
                engine_result,
                index=dates,
                title=input_path.stem,
            )
            if args.plot_output:
                figure.savefig(args.plot_output, dpi=150)
            if args.plot:
                import matplotlib.pyplot as plt

                plt.show()
        return 0
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print(f"demetrapy: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())