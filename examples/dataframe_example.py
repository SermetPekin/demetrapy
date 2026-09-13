"""Create a sample pandas DataFrame and seasonally adjust its values."""

from __future__ import annotations

import pandas as pd

from seasonal_pri import adjust


def create_input() -> pd.DataFrame:
    dates = pd.date_range("2015-01-01", periods=120, freq="MS")
    seasonal_pattern = [0, 4, 7, 5, 2, -1, -3, -2, 1, 3, 6, 2]
    values = [
        120 + index * 0.25 + seasonal_pattern[index % 12]
        for index in range(len(dates))
    ]
    return pd.DataFrame({"value": values}, index=dates).rename_axis("date")


def seasonally_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    first_date = frame.index[0]
    result = adjust(
        frame["value"].tolist(),
        frequency="Monthly",
        start_year=first_date.year,
        start_period=first_date.month,
        spec="RSA4",
    )
    return pd.DataFrame(result, index=frame.index).rename_axis("date")


if __name__ == "__main__":
    input_frame = create_input()
    adjusted_frame = seasonally_adjust(input_frame)

    print(adjusted_frame.head(12).round(3))
    adjusted_frame.to_csv("adjusted_dataframe.csv")
    print("\nSaved adjusted_dataframe.csv")