"""Adjust ten series with full parameters and a shared calendar pool."""

from __future__ import annotations

import pandas as pd

from demetrapy import adjust_dataframe, load_emissions_with_calendars


COMPONENTS = (
    "observed",
    "calendar_adjusted",
    "seasonally_adjusted",
    "trend",
    "seasonal",
    "irregular",
)

PREPROCESSING = {
    "transform": {
        "function": "Auto",
        "fct": 0.95,
        "units": False,
        "preliminary_check": True,
    },
    "automodel": {
        "enabled": True,
        "accept_default": False,
        "pcr": 0.95,
        "ub1": 0.97,
        "ub2": 0.91,
        "cancel": 0.05,
        "tsig": 1.0,
        "pc": 0.12,
        "ami_compare": False,
    },
    "estimate": {
        "tolerance": 1e-7,
        "exact_ml": True,
        "unit_root_limit": 0.96,
    },
}

OUTLIER_DETECTION = {
    "types": ["AO", "LS", "TC"],
    "critical_value": 3.5,
    "tc_rate": 0.7,
    "exact_ml": True,
}

SEATS = {
    "approximation_mode": "Legacy",
    "estimation_method": "Burman",
    "xl_boundary": 0.95,
    "seasonal_tolerance": 2.0,
    "trend_boundary": 0.5,
    "seasonal_boundary": 0.8,
    "seasonal_boundary_at_pi": 0.8,
    "prediction_length": 12,
}


def split_components(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        component: frame.xs(component, axis="columns", level="component")
        for component in COMPONENTS
    }


if __name__ == "__main__":
    dataset = load_emissions_with_calendars()

    result = adjust_dataframe(
        dataset.observations,
        calendar_pool=dataset.calendar_pool,
        user_defined_calendars=dataset.selections,
        method="tramoseats",
        spec="RSAfull",
        preprocessing=PREPROCESSING,
        outlier_detection=OUTLIER_DETECTION,
        seats=SEATS,
        detailed=True,
    )

    historical_frames = split_components(result.components)
    forecast_frames = split_components(result.to_forecast_frame())
    selected_variables = {
        variable
        for variables in dataset.selections.values()
        for variable in variables
    }
    unused_variables = set(dataset.calendar_pool.columns) - selected_variables

    assert unused_variables == {"unused_policy_index", "unused_fuel_price"}
    assert all(frame.shape == (120, 10) for frame in historical_frames.values())
    assert all(frame.shape == (12, 10) for frame in forecast_frames.values())
    assert all(frame.index.name == "date" for frame in historical_frames.values())
    assert all(frame.index.name == "date" for frame in forecast_frames.values())

    print("Calendar pool:", dataset.calendar_pool.shape)
    print("Calendar variables:", list(dataset.calendar_pool.columns))
    print("\nPer-series calendar mapping:")
    for target, variables in dataset.selections.items():
        print(f"  {target}: {variables}")
    print("\nUnused pool variables (accepted):", sorted(unused_variables))

    print("\nHistorical component DataFrames:")
    for component, frame in historical_frames.items():
        print(f"  {component}: {frame.shape}")
    print("\nForecast component DataFrames:")
    for component, frame in forecast_frames.items():
        print(
            f"  {component}: {frame.shape}, "
            f"{frame.index[0].date()} to {frame.index[-1].date()}"
        )

    print("\nCalendar-adjusted emissions:")
    print(historical_frames["calendar_adjusted"].tail(3).round(2))
    print("\nSeasonally adjusted emissions:")
    print(historical_frames["seasonally_adjusted"].tail(3).round(2))

    print("\nSelected models:")
    for target in dataset.observations.columns:
        model = result.for_series(target).arima_model
        print(f"  {target}: {model.notation if model else 'unavailable'}")