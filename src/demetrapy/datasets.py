"""Small deterministic datasets for examples and experimentation."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class CalendarDataset:
    observations: pd.DataFrame
    calendar_pool: pd.DataFrame
    selections: Mapping[str, tuple[str, ...]]


def load_monthly_retail() -> pd.DataFrame:
    """Return ten years of synthetic monthly sales and orders."""
    return load_retail_with_calendars().observations


def load_monthly_emissions() -> pd.DataFrame:
    """Return ten years of synthetic monthly emissions for ten sectors."""
    random_source = random.Random(20260915)
    index = pd.date_range("2015-01-01", periods=120, freq="MS")
    sectors = {
        "power": (82.0, -0.10, 13.0, 0),
        "transport": (61.0, 0.08, 8.0, 6),
        "industry": (48.0, -0.03, 5.0, 1),
        "residential": (35.0, -0.06, 11.0, 0),
        "commercial": (24.0, 0.02, 4.0, 11),
        "agriculture": (19.0, 0.01, 3.5, 4),
        "aviation": (14.0, 0.07, 3.0, 6),
        "shipping": (11.0, 0.03, 2.0, 7),
        "waste": (9.0, -0.01, 1.0, 8),
        "construction": (7.0, 0.04, 1.8, 5),
    }
    values = {}
    for sector, (level, trend, amplitude, peak_month) in sectors.items():
        values[sector] = [
            level
            + trend * position
            + amplitude
            * math.cos(2.0 * math.pi * (position - peak_month) / 12.0)
            + random_source.gauss(0.0, amplitude * 0.08)
            for position in range(len(index))
        ]
    return pd.DataFrame(values, index=index).rename_axis("date")


def load_emissions_with_calendars() -> CalendarDataset:
    """Return monthly emissions with a wider pool of calendar variables."""
    observations = load_monthly_emissions()
    random_source = random.Random(20260916)
    index = pd.date_range("2014-01-01", periods=144, freq="MS")
    weather_anomalies = [random_source.gauss(0.0, 1.2) for _ in index]
    working_days = [
        float(len(pd.bdate_range(timestamp, timestamp + pd.offsets.MonthEnd(0))))
        for timestamp in index
    ]
    calendar_pool = pd.DataFrame(
        {
            "heating_days": [
                max(
                    0.0,
                    14.0 * math.cos(2.0 * math.pi * position / 12.0)
                    + weather_anomalies[position],
                )
                for position in range(len(index))
            ],
            "cooling_days": [
                max(
                    0.0,
                    10.0 * math.cos(2.0 * math.pi * (position - 7) / 12.0)
                    - 0.7 * weather_anomalies[position],
                )
                for position in range(len(index))
            ],
            "working_days": working_days,
            "holiday_days": [
                float(
                    (timestamp.month in (1, 12))
                    + (timestamp.month == 4 and timestamp.year % 3 == 0)
                    + (timestamp.month == 11 and timestamp.year % 2 == 0)
                )
                for timestamp in index
            ],
            "mobility_index": [
                100.0 + 0.15 * position + 4.0 * math.sin(position / 5.0)
                for position in range(len(index))
            ],
            "industrial_days": [
                days - float((position + position // 12) % 3)
                for position, days in enumerate(working_days)
            ],
            "unused_policy_index": [float(position >= 72) for position in range(len(index))],
            "unused_fuel_price": [75.0 + 0.2 * position for position in range(len(index))],
        },
        index=index,
    ).rename_axis("date")
    return CalendarDataset(
        observations=observations,
        calendar_pool=calendar_pool,
        selections={
            "power": ("heating_days", "cooling_days", "working_days"),
            "transport": ("working_days", "holiday_days", "mobility_index"),
            "industry": ("working_days", "industrial_days"),
            "residential": ("heating_days", "cooling_days", "holiday_days"),
            "commercial": ("working_days", "heating_days", "cooling_days"),
            "agriculture": ("working_days",),
            "aviation": ("holiday_days", "mobility_index"),
            "shipping": ("industrial_days", "mobility_index"),
            "waste": ("working_days",),
            "construction": ("working_days", "industrial_days"),
        },
    )


def load_retail_with_calendars() -> CalendarDataset:
    """Return monthly retail observations and a wider calendar-variable pool."""
    random_source = random.Random(20260914)
    calendar_index = pd.date_range("2014-01-01", periods=144, freq="MS")
    retail_days = [float((index * 7) % 11 - 5) for index in range(144)]
    delivery_days = [float((index * 5 + 3) % 9 - 4) for index in range(144)]
    calendar_pool = pd.DataFrame(
        {
            "retail_days": retail_days,
            "delivery_days": delivery_days,
            "unused_calendar": [float(index % 2) for index in range(144)],
        },
        index=calendar_index,
    ).rename_axis("date")

    observation_index = pd.date_range("2015-01-01", periods=120, freq="MS")
    offset = 12
    sales_pattern = (-8.0, -5.0, -1.0, 3.0, 6.0, 9.0, 8.0, 4.0, 1.0, -2.0, -6.0, -9.0)
    orders_pattern = (-5.0, -2.0, 1.0, 4.0, 7.0, 6.0, 3.0, 0.0, -2.0, -4.0, -3.0, -1.0)
    sales = []
    orders = []
    for index in range(120):
        calendar_position = offset + index
        sales.append(
            180.0
            + 0.35 * index
            + sales_pattern[index % 12]
            + 1.8 * retail_days[calendar_position]
            + random_source.gauss(0.0, 1.2)
        )
        orders.append(
            95.0
            + 0.22 * index
            + orders_pattern[index % 12]
            + 1.1 * retail_days[calendar_position]
            + 1.5 * delivery_days[calendar_position]
            + random_source.gauss(0.0, 0.9)
        )
    observations = pd.DataFrame(
        {"sales": sales, "orders": orders}, index=observation_index
    ).rename_axis("date")
    return CalendarDataset(
        observations=observations,
        calendar_pool=calendar_pool,
        selections={
            "sales": ("retail_days",),
            "orders": ("retail_days", "delivery_days"),
        },
    )


def load_quarterly_production() -> pd.DataFrame:
    """Return twenty years of synthetic quarterly production."""
    random_source = random.Random(20260914)
    index = pd.date_range("2005-01-01", periods=80, freq="QS")
    seasonal_pattern = (-4.0, 2.0, 5.0, -3.0)
    values = [
        100.0
        + 0.4 * position
        + 1.5 * math.sin(position / 10.0)
        + seasonal_pattern[position % 4]
        + random_source.gauss(0.0, 0.6)
        for position in range(len(index))
    ]
    return pd.DataFrame({"production": values}, index=index).rename_axis("quarter")