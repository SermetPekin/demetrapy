"""Create a sample pandas DataFrame and seasonally adjust its values."""

from __future__ import annotations

import pandas as pd

from demetrapy import DataFrameAdjustmentResult, adjust_dataframe


def create_input() -> pd.DataFrame:
    dates = pd.date_range("2015-01-01", periods=120, freq="MS")
    seasonal_pattern = [0, 4, 7, 5, 2, -1, -3, -2, 1, 3, 6, 2]
    values = [
        120 + index * 0.25 + seasonal_pattern[index % 12]
        for index in range(len(dates))
    ]
    return pd.DataFrame({"value": values}, index=dates).rename_axis("date")


def seasonally_adjust(frame: pd.DataFrame) -> DataFrameAdjustmentResult:
    return adjust_dataframe(
        frame,
        spec="RSA4",
        forecast_horizon=12,
        detailed=True,
    )


if __name__ == "__main__":
    input_frame = create_input()
    result = seasonally_adjust(input_frame)
    adjusted_frame = result.to_compact_frame()["value"]

    assert result.detailed_series is not None
    detailed_frame = result.detailed_series["value"]
    forecast_columns = [
        "final.y_f",
        "preprocessing.ycal_f",
        "final.sa_f",
        "final.t_f",
        "final.s_f",
        "final.i_f",
    ]
    forecast_frame = detailed_frame[forecast_columns].dropna(how="all")
    series_result = result.for_series("value")

    print("Historical components:")
    print(adjusted_frame.head(12).round(3))
    print("\nForecast components:")
    print(forecast_frame.round(3))
    print(f"\nDetailed series: {len(detailed_frame.columns)}")
    print(f"Diagnostics: {len(series_result.diagnostics)}")
    print(f"Messages: {len(series_result.messages)}")

    adjusted_frame.to_csv("adjusted_dataframe.csv")
    forecast_frame.to_csv("forecast_dataframe.csv")
    detailed_frame.to_csv("detailed_dataframe.csv")
    print(
        "\nSaved adjusted_dataframe.csv, forecast_dataframe.csv, "
        "and detailed_dataframe.csv"
    )