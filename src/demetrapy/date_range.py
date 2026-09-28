from dataclasses import dataclass
from typing import Literal

import pandas as pd

MonthlyFreqType = Literal["M", "Monthly"]
QuarterlyFreqType = Literal["Q", "Quarterly"]
FreqType = MonthlyFreqType | QuarterlyFreqType


@dataclass
class DateRange:
    start: str = "2015-01-01"
    periods: int = 120
    freq: FreqType = "M"

    def __str__(self) -> str:
        return f"DateRange-{self.start}[{self.periods},{self.freq}]\n{self.dates[0:3]}"

    def __post_init__(self) -> None:
        valid_freqs = {"M", "Monthly", "Q", "Quarterly"}
        if self.freq not in valid_freqs:
            raise ValueError(f"Invalid freq: {self.freq}. Choose from {valid_freqs}")

    @property
    def dates(self) -> pd.DatetimeIndex:
        frequencies = {
            "M": "MS",
            "Monthly": "MS",
            "Q": "QS",
            "Quarterly": "QS",
            "QE": "QE",
            "QS": "QS",
        }
        return pd.date_range(
            self.start,
            periods=self.periods,
            freq=frequencies[self.freq],
        )
    def __call__(self) -> pd.DatetimeIndex:
        return self.dates
    


@dataclass
class DateRangeMonth(DateRange):
    """Monthly date range using month-start timestamps."""

    freq: MonthlyFreqType = "Monthly"

    def __post_init__(self) -> None:
        if self.freq not in {"M", "Monthly"}:
            raise ValueError("DateRangeMonth freq must be 'M' or 'Monthly'")


@dataclass
class DateRangeQuarter(DateRange):
    """Quarterly date range using quarter-start timestamps."""

    freq: QuarterlyFreqType = "Quarterly"

    def __post_init__(self) -> None:
        if self.freq not in {"Q", "Quarterly"}:
            raise ValueError("DateRangeQuarter freq must be 'Q' or 'Quarterly'")


    

def _create_input() -> pd.DataFrame:
    dates = DateRangeMonth("2015-01-01", 120)()
    seasonal_pattern = [0, 4, 7, 5, 2, -1, -3, -2, 1, 3, 6, 2]
    values = [
        120 + index * 0.25 + seasonal_pattern[index % 12]
        for index in range(len(dates))
    ]
    return pd.DataFrame({"value": values}, index=dates).rename_axis("date")


if __name__ == "__main__":
    print(DateRangeMonth("2015-01-01", 120))
    print(DateRangeQuarter("2015-01-01", 40))