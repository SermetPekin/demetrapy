"""Run quarterly data through DataFrame, CSV, and sequence APIs."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from demetrapy import (
    TramoSeatsConfig,
    X13Config,
    adjust,
    adjust_csv,
    adjust_dataframe,
    load_quarterly_production,
)


def main() -> None:
    data = load_quarterly_production()
    adjusted = {}

    configurations = {
        "x13": X13Config(spec="RSA4"),
        "tramoseats": TramoSeatsConfig(spec="RSA4"),
    }
    for method, config in configurations.items():
        result = adjust_dataframe(data, config=config)
        series_result = result.for_series("production")
        assert series_result.observed.frequency == "Quarterly"
        adjusted[method] = result.seasonally_adjusted["production"]

    comparison = pd.DataFrame(adjusted)
    comparison["difference"] = comparison["x13"] - comparison["tramoseats"]
    print(comparison.tail(8).round(3))

    values = data["production"].tolist()
    sequence_result = adjust(
        values,
        frequency="Quarterly",
        start_year=data.index[0].year,
        start_period=1,
        config=X13Config(spec="RSA4"),
    )

    with TemporaryDirectory() as directory:
        csv_path = Path(directory) / "quarterly_production.csv"
        data.rename(columns={"production": "value"}).rename_axis("date").to_csv(
            csv_path
        )
        csv_result = adjust_csv(csv_path, config=X13Config(spec="RSA4"))

    assert sequence_result.observed.frequency == "Quarterly"
    assert csv_result.observed.frequency == "Quarterly"
    print("\nFrequency rules:")
    print("  DataFrame: inferred from the DatetimeIndex")
    print("  CSV: inferred from regular ISO dates")
    print('  Sequence: pass frequency="Quarterly" explicitly')


if __name__ == "__main__":
    main()