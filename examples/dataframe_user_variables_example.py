"""Adjust target columns with user-defined trading-day calendar weights."""

from __future__ import annotations

import pandas as pd

from seasonal_pri import adjust_dataframe


def create_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar_dates = pd.date_range("2014-01-01", periods=168, freq="MS")
    dates = calendar_dates[12:156]
    seasonal_pattern = [0, 4, 7, 5, 2, -1, -3, -2, 1, 3, 6, 2]
    series_frame = pd.DataFrame(
        {
            "sales": [
                120 + index * 0.25 + seasonal_pattern[index % 12]
                for index in range(len(dates))
            ],
            "orders": [
                80 + index * 0.15 + seasonal_pattern[(index + 2) % 12]
                for index in range(len(dates))
            ],
        },
        index=dates,
    ).rename_axis("date")
    calendar_pool = pd.DataFrame(
        {
            "retail_td": [float((index * 5) % 7 - 3) for index in range(168)],
            "delivery_td": [float((index * 3) % 5 - 2) for index in range(168)],
            "unused_calendar": [float(index % 2) for index in range(168)],
        },
        index=calendar_dates,
    ).rename_axis("date")
    return series_frame, calendar_pool


if __name__ == "__main__":
    observations, calendars = create_inputs()
    selected_calendars = {
        "sales": ["retail_td"],
        "orders": ["retail_td", "delivery_td"],
    }
    result = adjust_dataframe(
        observations,
        calendar_pool=calendars,
        user_defined_calendars=selected_calendars,
        method="tramoseats",
        spec="RSA4",
        seats={"prediction_length": 12},
        detailed=True,
    )

    print("Available calendar columns:", list(calendars.columns))
    print("Calendars selected by target:", selected_calendars)
    print("Output frame shape:", result.series.shape)
    print("Diagnostics by target:", {
        target: len(values) for target, values in result.diagnostics.items()
    })
    sales_history = result.series.loc[
        :, [("sales", "final.y"), ("sales", "final.sa")]
    ].dropna()
    print(sales_history.head(12).round(3))
    print("Sales forecast:")
    print(result.series.loc[:, ("sales", "final.sa_f")].dropna().round(3))
