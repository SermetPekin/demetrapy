"""Run a complete TRAMO/SEATS specification with a UserDefined calendar."""

from __future__ import annotations

import argparse
import calendar
import math
from pathlib import Path
import random

import pandas as pd

from seasonal_pri import adjust_dataframe


EXPLICIT_ARIMA = {
    "p": 0,
    "d": 1,
    "q": 1,
    "bp": 0,
    "bd": 1,
    "bq": 1,
    "mean": False,
}

TRAMO_AUTOMODEL = {
    "enabled": True,
    "accept_default": False,
    "pcr": 0.95,
    "ub1": 0.97,
    "ub2": 0.91,
    "cancel": 0.05,
    "tsig": 1.0,
    "pc": 0.12,
    "ami_compare": False,
}


def create_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar_dates = pd.date_range("2009-01-01", periods=216, freq="MS")
    calendar_pool = pd.DataFrame(
        {
            "company_working_days": [
                _working_day_contrast(date.year, date.month)
                for date in calendar_dates
            ],
            "unused_month_length": [
                float(calendar.monthrange(date.year, date.month)[1])
                for date in calendar_dates
            ],
        },
        index=calendar_dates,
    ).rename_axis("date")

    dates = calendar_dates[12:192]
    random_source = random.Random(20260914)
    seasonal_pattern = (
        -8.0,
        -5.0,
        -2.0,
        1.0,
        4.0,
        7.0,
        9.0,
        6.0,
        2.0,
        -1.0,
        -4.0,
        -9.0,
    )
    calendar_effect = calendar_pool.loc[dates, "company_working_days"]
    values = [
        150.0
        + 0.22 * index
        + 2.0 * math.sin(index / 24.0)
        + seasonal_pattern[index % 12]
        + 1.8 * calendar_effect.iloc[index]
        + random_source.gauss(0.0, 1.0)
        for index in range(len(dates))
    ]
    observations = pd.DataFrame(
        {"turnover": values},
        index=dates,
    ).rename_axis("date")
    return observations, calendar_pool


def _working_day_contrast(year: int, month: int) -> float:
    weekday_count = 0
    weekend_count = 0
    for week in calendar.monthcalendar(year, month):
        weekday_count += sum(day != 0 for day in week[:5])
        weekend_count += sum(day != 0 for day in week[5:])
    return float(weekday_count - 2.5 * weekend_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--auto-model",
        action="store_true",
        help="use every TRAMO automodel option instead of explicit ARIMA orders",
    )
    arguments = parser.parse_args()
    observations, calendars = create_inputs()
    selected_calendars = {"turnover": ["company_working_days"]}

    result = adjust_dataframe(
        observations,
        calendar_pool=calendars,
        user_defined_calendars=selected_calendars,
        method="tramoseats",
        spec="RSAfull",
        preprocessing={
            "transform": {
                "function": "None",
                "fct": 0.95,
                "units": False,
                "preliminary_check": True,
            },
            **(
                {"automodel": TRAMO_AUTOMODEL}
                if arguments.auto_model
                else {"arima": EXPLICIT_ARIMA}
            ),
            "estimate": {
                "tolerance": 1e-7,
                "exact_ml": True,
                "unit_root_limit": 0.96,
            },
        },
        outlier_detection={
            "types": ["AO", "LS", "TC"],
            "critical_value": 3.5,
            "tc_rate": 0.7,
            "exact_ml": True,
        },
        seats={
            "approximation_mode": "Legacy",
            "estimation_method": "Burman",
            "xl_boundary": 0.95,
            "seasonal_tolerance": 2.0,
            "trend_boundary": 0.5,
            "seasonal_boundary": 0.8,
            "seasonal_boundary_at_pi": 0.8,
            "prediction_length": 12,
        },
        detailed=True,
    )

    model = result.arima_models["turnover"]
    if model is None:
        raise RuntimeError("TRAMO/SEATS did not report a fitted ARIMA model")

    output_columns = [
        ("turnover", name)
        for name in ("final.y", "final.sa", "final.t", "final.s", "final.i", "final.sa_f")
    ]
    output = result.series.loc[:, output_columns].dropna(how="all")
    output_path = Path("tramoseats_user_calendar_results.csv")
    output.to_csv(output_path)

    print("Calendar pool:", list(calendars.columns))
    print("Selected UserDefined calendar:", selected_calendars["turnover"])
    print("Built-in trading days: disabled by UserDefined selection")
    print(f"Fitted model: {model.notation}, mean={model.mean}, automatic={model.automatic}")
    print("Diagnostics:", len(result.diagnostics["turnover"]))
    print("Messages:", len(result.messages["turnover"]))
    print("Forecast:")
    print(result.series[("turnover", "final.sa_f")].dropna().round(3))
    print(f"Saved detailed components to {output_path.resolve()}")