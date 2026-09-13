"""Compare X13 and TRAMO/SEATS results for the same monthly series."""

from __future__ import annotations

import math
from pathlib import Path
import random

import pandas as pd

from demetrapy import COMPACT_COMPONENTS, adjust_dataframe


def create_input() -> pd.DataFrame:
    random_source = random.Random(20260914)
    dates = pd.date_range("2010-01-01", periods=180, freq="MS")
    seasonal_pattern = (-7.0, -4.0, -1.0, 2.0, 5.0, 8.0, 9.0, 5.0, 1.0, -2.0, -6.0, -10.0)
    values = [
        120.0
        + 0.18 * index
        + 2.5 * math.sin(index / 20.0)
        + seasonal_pattern[index % 12]
        + random_source.gauss(0.0, 1.0)
        for index in range(len(dates))
    ]
    return pd.DataFrame({"value": values}, index=dates).rename_axis("date")


def compare_methods(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    method_results = {}
    for method in ("x13", "tramoseats"):
        adjusted = adjust_dataframe(data, method=method, spec="RSA4")
        method_results[method] = adjusted["value"]

    x13 = method_results["x13"]
    tramoseats = method_results["tramoseats"]
    differences = x13 - tramoseats
    comparison = pd.concat(
        {
            "x13": x13,
            "tramoseats": tramoseats,
            "difference": differences,
        },
        axis=1,
    )
    metrics = pd.DataFrame(
        {
            component: _comparison_metrics(x13[component], tramoseats[component])
            for component in COMPACT_COMPONENTS
        }
    ).T
    metrics.index.name = "component"
    return comparison, metrics


def _comparison_metrics(left: pd.Series, right: pd.Series) -> dict[str, float]:
    difference = left - right
    return {
        "rmse": float(math.sqrt((difference**2).mean())),
        "max_absolute_difference": float(difference.abs().max()),
        "correlation": float(left.corr(right)),
    }


if __name__ == "__main__":
    input_frame = create_input()
    result_frame, summary = compare_methods(input_frame)
    output_path = Path("method_comparison.csv")
    result_frame.to_csv(output_path)

    print("X13 versus TRAMO/SEATS component metrics:")
    print(summary.round(6))
    print("\nSeasonally adjusted series preview:")
    print(result_frame.loc[:, [("x13", "sa"), ("tramoseats", "sa"), ("difference", "sa")]].head(12).round(3))
    print(f"\nSaved aligned results to {output_path.resolve()}")