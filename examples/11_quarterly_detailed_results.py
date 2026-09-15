"""Inspect quarterly TRAMO/SEATS history, forecasts, and model results."""

from __future__ import annotations

import pandas as pd

from demetrapy import (
    DataFrameAdjustmentResult,
    TramoSeatsConfig,
    adjust_dataframe,
    load_quarterly_production,
)


def seasonally_adjust(frame: pd.DataFrame) -> DataFrameAdjustmentResult:
    return adjust_dataframe(
        frame,
        config=TramoSeatsConfig(
            spec="RSAfull",
            preprocessing={"automodel": {"enabled": True}},
            seats={"prediction_length": 4},
        ),
        detailed=True,
    )


if __name__ == "__main__":
    input_frame = load_quarterly_production()
    result = seasonally_adjust(input_frame)
    history = result.components["production"]
    compact_history = result.to_compact_frame()["production"]
    forecasts = result.to_forecast_frame()["production"]
    compact_forecasts = result.to_forecast_frame(compact=True)["production"]
    combined = result.to_combined_frame(compact=True)["production"]
    combined_sa = combined["sa"].rename("seasonally_adjusted")
    series_result = result.for_series("production")

    expected_forecast_index = pd.period_range(
        start=input_frame.index[-1].to_period("Q") + 1,
        periods=4,
        freq="Q",
    ).to_timestamp()
    pd.testing.assert_index_equal(
        forecasts.index,
        expected_forecast_index.rename(input_frame.index.name),
    )

    assert result.detailed_series is not None
    detailed_frame = result.detailed_series["production"]

    print("Quarterly TRAMO/SEATS historical components:")
    print(history.tail(3).round(3))
    print("\nCompact historical columns:")
    print(compact_history.tail(3).round(3))
    print("\nQuarterly forecast DataFrame:")
    print(forecasts.round(3))
    print("\nCompact quarterly forecast columns:")
    print(compact_forecasts.round(3))
    print("\nSeasonally adjusted history + forecast:")
    print(combined_sa.tail(7).round(3))
    print(f"\nLast observation: {input_frame.index[-1].date()}")
    print(f"Forecast range: {forecasts.index[0].date()} to {forecasts.index[-1].date()}")
    print(f"Method: {series_result.method}")
    print(f"Specification: {series_result.specification}")
    if series_result.arima_model is not None:
        print(f"ARIMA model: {series_result.arima_model.notation}")
    print(f"\nDetailed series: {len(detailed_frame.columns)}")
    print(f"Diagnostics: {len(series_result.diagnostics)}")
    print(f"Messages: {len(series_result.messages)}")

    compact_history.to_csv("quarterly_historical_compact.csv")
    compact_forecasts.to_csv("quarterly_forecast_compact.csv")
    combined_sa.to_csv("quarterly_combined_seasonally_adjusted.csv")
    detailed_frame.to_csv("quarterly_detailed_dataframe.csv")
    print(
        "\nSaved quarterly_historical_compact.csv, "
        "quarterly_forecast_compact.csv, "
        "quarterly_combined_seasonally_adjusted.csv, and "
        "quarterly_detailed_dataframe.csv"
    )