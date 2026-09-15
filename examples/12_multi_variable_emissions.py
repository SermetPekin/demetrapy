"""Adjust ten monthly emissions variables into component DataFrames."""

from __future__ import annotations

import pandas as pd

from demetrapy import TramoSeatsConfig, adjust_dataframe, load_monthly_emissions


COMPONENTS = (
    "observed",
    "calendar_adjusted",
    "seasonally_adjusted",
    "trend",
    "seasonal",
    "irregular",
)


def split_component_frames(frame: pd.DataFrame) -> tuple[
    dict[str, pd.DataFrame],
    dict[str, pd.DataFrame],
]:
    result = adjust_dataframe(
        frame,
        config=TramoSeatsConfig(
            spec="RSAfull",
            preprocessing={"automodel": {"enabled": True}},
            seats={"prediction_length": 12},
        ),
    )
    historical = {
        component: result.components.xs(
            component,
            axis="columns",
            level="component",
        )
        for component in COMPONENTS
    }
    forecasts = result.to_forecast_frame()
    forecast = {
        component: forecasts.xs(
            component,
            axis="columns",
            level="component",
        )
        for component in COMPONENTS
    }
    return historical, forecast


if __name__ == "__main__":
    emissions = load_monthly_emissions()
    historical_frames, forecast_frames = split_component_frames(emissions)

    assert all(frame.shape == (120, 10) for frame in historical_frames.values())
    assert all(frame.shape == (12, 10) for frame in forecast_frames.values())
    assert all(frame.index.name == "date" for frame in historical_frames.values())
    assert all(frame.index.name == "date" for frame in forecast_frames.values())
    assert forecast_frames["seasonally_adjusted"].index[0] > emissions.index[-1]

    print("Input emissions DataFrame:", emissions.shape)
    print(emissions.tail(3).round(2))

    print("\nHistorical component DataFrames:")
    for component, frame in historical_frames.items():
        print(f"  {component}: {frame.shape}")

    print("\nForecast component DataFrames:")
    for component, frame in forecast_frames.items():
        print(
            f"  {component}: {frame.shape}, "
            f"{frame.index[0].date()} to {frame.index[-1].date()}"
        )
    print("\nSeasonally adjusted emissions:")
    print(historical_frames["seasonally_adjusted"].tail(3).round(2))
    print("\nSeasonally adjusted forecasts:")
    print(forecast_frames["seasonally_adjusted"].round(2))