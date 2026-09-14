"""Adjust and compare one quarterly series with X13 and TRAMO/SEATS."""

from __future__ import annotations

import math
import random

import pandas as pd

from demetrapy import adjust_dataframe


def create_quarterly_data() -> pd.DataFrame:
    random_source = random.Random(20260914)
    dates = pd.date_range("2005-01-01", periods=80, freq="QS")
    seasonal_pattern = (-4.0, 2.0, 5.0, -3.0)
    values = [
        100.0
        + 0.4 * index
        + 1.5 * math.sin(index / 10.0)
        + seasonal_pattern[index % 4]
        + random_source.gauss(0.0, 0.6)
        for index in range(len(dates))
    ]
    return pd.DataFrame({"gdp": values}, index=dates).rename_axis("quarter")


if __name__ == "__main__":
    observations = create_quarterly_data()
    explicit_arima = {
        "p": 0,
        "d": 1,
        "q": 1,
        "bp": 0,
        "bd": 1,
        "bq": 1,
        "mean": False,
    }
    adjusted = {}

    for method in ("x13", "tramoseats"):
        result = adjust_dataframe(
            observations,
            method=method,
            spec="RSA4",
            preprocessing={"arima": explicit_arima},
            detailed=True,
        )
        model = result.for_series("gdp").arima_model
        if model is None:
            raise RuntimeError(f"{method} did not report a fitted ARIMA model")
        assert result.detailed_series is not None
        adjusted[method] = result.detailed_series[("gdp", "final.sa")].dropna()
        print(
            f"{method}: {model.notation}, frequency={model.period}, "
            f"automatic={model.automatic}"
        )

    comparison = pd.concat(adjusted, axis=1)
    comparison["difference"] = comparison["x13"] - comparison["tramoseats"]
    print("\nQuarterly seasonally adjusted comparison:")
    print(comparison.head(8).round(3))