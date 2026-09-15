from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import AdjustmentConfig
from .csv_io import (
    PERIODS_PER_YEAR,
    _execute_csv,
    _frequency_from_dates,
    _read_csv,
    _start,
    _write_csv,
)
from .engine import adjust
from .plotting import plot_adjustment
from .readiness import is_ready, run_readiness_checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demetrapy",
        description="Seasonally adjust a regular CSV series with JDemetra+ core.",
        epilog=(
            "Other commands: 'demetrapy check', 'demetrapy validate CONFIG', and "
            "'demetrapy init-config --method {x13,tramoseats}'."
        ),
    )
    parser.add_argument(
        "input", nargs="?", type=Path, help="CSV containing date and value columns"
    )
    parser.add_argument(
        "-d", "--data", type=Path, help="CSV data file (alternative to positional input)"
    )
    parser.add_argument("-c", "--config", type=Path, help="JSON adjustment configuration")
    parser.add_argument("-o", "--output", type=Path, help="output CSV (default: stdout)")
    parser.add_argument("--audit", type=Path, help="write structured audit records")
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


def _validate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demetrapy validate",
        description="Validate a configuration without starting Java.",
    )
    parser.add_argument("config", type=Path, help="JSON configuration file")
    parser.add_argument("--data", type=Path, help="also validate CSV columns and dates")
    parser.add_argument(
        "--output", type=Path, help="write the normalized configuration as JSON"
    )
    return parser


def _init_config_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demetrapy init-config",
        description="Create a validated starter configuration.",
    )
    parser.add_argument("--method", required=True, choices=("x13", "tramoseats"))
    parser.add_argument("--output", type=Path, help="destination JSON file")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    return parser


def _run_validate(argv: Sequence[str]) -> int:
    args = _validate_parser().parse_args(argv)
    config = AdjustmentConfig.load(args.config)
    if args.data:
        dates, _, _ = _read_csv(args.data, config)
        data_frequency = _frequency_from_dates(dates)
        if config.frequency != data_frequency:
            raise ValueError(
                f"CSV dates are {data_frequency}, but configuration frequency is "
                f"{config.frequency}"
            )
        _start(dates, config.frequency)
    if args.output:
        args.output.write_text(
            json.dumps(config.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"Valid configuration: method={config.method}, "
        f"spec={config.spec}, frequency={config.frequency}"
    )
    if args.data:
        print(f"Valid data: {args.data}")
    return 0


def _run_init_config(argv: Sequence[str]) -> int:
    args = _init_config_parser().parse_args(argv)
    output = args.output or Path(f"demetrapy-{args.method}.json")
    if output.exists() and not args.force:
        raise ValueError(f"refusing to overwrite existing file: {output}; use --force")
    config = AdjustmentConfig.template(args.method)
    config.validate()
    output.write_text(
        json.dumps(config.to_dict(omit_empty=True), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {args.method} configuration: {output}")
    return 0


def _run_check(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="demetrapy check",
        description="Check whether this environment is ready to run demetrapy.",
    )
    parser.parse_args(argv)
    checks = run_readiness_checks()
    width = max(len(check.name) for check in checks)
    for check in checks:
        print(f"{check.name:<{width}}  {check.status:<7}  {check.detail}")
        if check.action:
            print(f"{'':<{width}}           Fix: {check.action}")
    print()
    if is_ready(checks):
        print("demetrapy is ready.")
        return 0
    print("demetrapy is not ready. Apply the Fix steps above, then run 'demetrapy check' again.")
    return 2


def run(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments[:1] == ["check"]:
            return _run_check(arguments[1:])
        if arguments[:1] == ["validate"]:
            return _run_validate(arguments[1:])
        if arguments[:1] == ["init-config"]:
            return _run_init_config(arguments[1:])

        args = _parser().parse_args(arguments)
        if args.input and args.data:
            raise ValueError("provide the data file either positionally or with --data, not both")
        input_path = args.data or args.input
        if input_path is None:
            raise ValueError("a data file is required; use --data FILE or a positional path")
        overrides = {
            name: getattr(args, name)
            for name in ("method", "spec", "frequency", "date_column", "value_column")
            if getattr(args, name) is not None
        }
        wants_plot = args.plot or args.plot_output is not None
        dates, engine_result = _execute_csv(
            input_path,
            config=args.config,
            overrides=overrides,
            output=args.output,
            audit=args.audit,
            detailed=wants_plot,
            adjustment_function=adjust,
        )
        result = engine_result.to_compact_dict()
        if not args.output:
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
    except (ImportError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"demetrapy: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())