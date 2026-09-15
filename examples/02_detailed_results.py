"""Inspect complete TRAMO/SEATS history, forecasts, and model results."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from demetrapy import DataFrameAdjustmentResult, TramoSeatsConfig, adjust_dataframe


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
        config=TramoSeatsConfig(
            spec="RSAfull",
            preprocessing={"automodel": {"enabled": True}},
            seats={"prediction_length": 12},
        ),
        detailed=True,
    )


if __name__ == "__main__":
    output_directory = Path("example_output")
    output_directory.mkdir(exist_ok=True)
    input_frame = create_input()
    result = seasonally_adjust(input_frame)
    history = result.components["value"]
    compact_history = result.to_compact_frame()["value"]
    forecasts = result.to_forecast_frame()["value"]
    compact_forecasts = result.to_forecast_frame(compact=True)["value"]
    combined = result.to_combined_frame(compact=True)["value"]
    combined_sa = combined["sa"].rename("seasonally_adjusted")
    series_result = result.for_series("value")

    assert result.detailed_series is not None
    detailed_frame = result.detailed_series["value"]

    print("TRAMO/SEATS historical components:")
    print(history.tail(3).round(3))
    print("\nCompact historical columns:")
    print(compact_history.tail(3).round(3))
    print("\nForecast DataFrame:")
    print(forecasts.round(3))
    print("\nCompact forecast columns:")
    print(compact_forecasts.round(3))
    print("\nSeasonally adjusted history + forecast:")
    print(combined_sa.tail(15).round(3))
    print(f"\nMethod: {series_result.method}")
    print(f"Specification: {series_result.specification}")
    if series_result.arima_model is not None:
        print(f"ARIMA model: {series_result.arima_model.notation}")
    print(f"\nDetailed series: {len(detailed_frame.columns)}")
    print(f"Diagnostics: {len(series_result.diagnostics)}")
    print(f"Messages: {len(series_result.messages)}")

    compact_history.to_csv(output_directory / "historical_compact.csv")
    compact_forecasts.to_csv(output_directory / "forecast_compact.csv")
    combined_sa.to_csv(output_directory / "combined_seasonally_adjusted.csv")
    detailed_frame.to_csv(output_directory / "detailed_dataframe.csv")
    print(f"\nSaved CSV results under {output_directory}/")