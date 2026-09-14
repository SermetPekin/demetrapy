"""Pandas-facing seasonal adjustment helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

from .engine import AdjustmentResult, adjust

_FREQUENCIES = {
    1: "Monthly",
    3: "Quarterly",
    6: "HalfYearly",
    12: "Yearly",
}


@dataclass(frozen=True)
class DataFrameAdjustmentResult:
    components: Any
    results: Mapping[Any, AdjustmentResult]
    detailed_series: Any | None = None

    def for_series(self, target: Any) -> AdjustmentResult:
        try:
            return self.results[target]
        except KeyError as error:
            raise KeyError(f"unknown result series: {target}") from error

    def to_compact_frame(self) -> Any:
        aliases = {
            "observed": "y",
            "calendar_adjusted": "ycal",
            "seasonally_adjusted": "sa",
            "trend": "t",
            "seasonal": "s",
            "irregular": "i",
        }
        return self.components.rename(columns=aliases, level="component")

    @property
    def observed(self) -> Any:
        return self._component("observed")

    @property
    def seasonally_adjusted(self) -> Any:
        return self._component("seasonally_adjusted")

    @property
    def calendar_adjusted(self) -> Any:
        return self._component("calendar_adjusted")

    @property
    def trend(self) -> Any:
        return self._component("trend")

    @property
    def seasonal(self) -> Any:
        return self._component("seasonal")

    @property
    def irregular(self) -> Any:
        return self._component("irregular")

    def _component(self, name: str) -> Any:
        return self.components.xs(name, axis=1, level="component")


def adjust_dataframe(
    data: Any,
    *,
    calendar_pool: Any | None = None,
    user_defined_calendars: Mapping[Any, Sequence[Any]] | None = None,
    detailed: bool = False,
    **adjustment_options: Any,
) -> DataFrameAdjustmentResult:
    """Adjust DataFrame columns with optional user-defined trading-day variables."""
    pd = _pandas()
    frame = data.to_frame() if isinstance(data, pd.Series) else data
    _validate_frame(frame, "data", pd)
    data_frequency, data_periods = _frequency_and_periods(frame.index, "data", pd)

    mapping = dict(user_defined_calendars or {})
    unknown_targets = set(mapping) - set(frame.columns)
    if unknown_targets:
        raise ValueError(f"unknown target columns: {_column_list(unknown_targets)}")

    reserved = {"frequency", "start_year", "start_period", "calendar_variables"}
    conflicting = reserved.intersection(adjustment_options)
    if conflicting:
        raise ValueError(
            f"adjustment_options cannot override: {_column_list(conflicting)}"
        )

    pool = None
    pool_frequency = None
    pool_periods = None
    if mapping:
        if calendar_pool is None:
            raise ValueError("calendar_pool is required when calendars are selected")
        pool = calendar_pool
        _validate_frame(pool, "calendar_pool", pd)
        pool_frequency, pool_periods = _frequency_and_periods(
            pool.index, "calendar_pool", pd
        )
        if pool_frequency != data_frequency:
            raise ValueError(
                "calendar_pool frequency must match the target data frequency"
            )
        missing_periods = data_periods.difference(pool_periods)
        if len(missing_periods):
            raise ValueError("calendar_pool must cover every target data period")

    component_frames = []
    detailed_frames = []
    results = {}
    for target in frame.columns:
        selected_columns = list(mapping.get(target, ()))
        if isinstance(mapping.get(target), (str, bytes)):
            raise ValueError(f"calendar selection for '{target}' must be a sequence")
        if len(selected_columns) != len(set(selected_columns)):
            raise ValueError(f"calendar selection for '{target}' contains duplicates")

        calendar_variables = []
        if selected_columns:
            assert pool is not None and pool_frequency is not None and pool_periods is not None
            missing_columns = set(selected_columns) - set(pool.columns)
            if missing_columns:
                raise ValueError(
                    f"calendar_pool is missing columns: {_column_list(missing_columns)}"
                )
            selected = set(selected_columns)
            pool_start = pool_periods[0]
            calendar_variables = [
                {
                    "name": f"variable_{position}",
                    "values": pool[column].tolist(),
                    "frequency": pool_frequency,
                    "start_year": pool_start.year,
                    "start_period": _start_period(pool_start, pool_frequency),
                    "selected": column in selected,
                }
                for position, column in enumerate(pool.columns)
            ]

        target_start = data_periods[0]
        result = adjust(
            frame[target].tolist(),
            frequency=data_frequency,
            start_year=target_start.year,
            start_period=_start_period(target_start, data_frequency),
            calendar_variables=calendar_variables,
            detailed=detailed,
            **adjustment_options,
        )
        results[target] = result
        component_frames.append(_components_frame(target, result, frame.index, pd))
        if detailed:
            detailed_frames.append(_detailed_frame(target, result, pd))

    detailed_series = None
    if detailed_frames:
        detailed_series = (
            pd.concat(detailed_frames, axis=1)
            .sort_index()
            .rename_axis(frame.index.name)
        )
    return DataFrameAdjustmentResult(
        components=pd.concat(component_frames, axis=1).rename_axis(frame.index.name),
        results=results,
        detailed_series=detailed_series,
    )


def _components_frame(
    target: Any,
    result: AdjustmentResult,
    index: Any,
    pd: Any,
) -> Any:
    frame = pd.DataFrame(
        {
            "observed": result.observed.values,
            "calendar_adjusted": result.calendar_adjusted.values,
            "seasonally_adjusted": result.seasonally_adjusted.values,
            "trend": result.trend.values,
            "seasonal": result.seasonal.values,
            "irregular": result.irregular.values,
        },
        index=index,
    )
    frame.columns = pd.MultiIndex.from_product(
        [[target], frame.columns], names=["series", "component"]
    )
    return frame


def _detailed_frame(target: Any, result: AdjustmentResult, pd: Any) -> Any:
    detailed = _output_frame(result, pd)
    detailed.columns = pd.MultiIndex.from_product(
        [[target], detailed.columns], names=["series", "output"]
    )
    return detailed


def _output_frame(result: AdjustmentResult, pd: Any) -> Any:
    columns = {}
    for name, output in result.series.items():
        month = {
            "Monthly": output.start_period,
            "Quarterly": (output.start_period - 1) * 3 + 1,
            "HalfYearly": (output.start_period - 1) * 6 + 1,
            "Yearly": 1,
        }[output.frequency]
        aliases = {
            "Monthly": "M",
            "Quarterly": "Q-DEC",
            "HalfYearly": "2Q-DEC",
            "Yearly": "Y-DEC",
        }
        start = pd.Timestamp(output.start_year, month, 1)
        index = pd.period_range(
            start=start, periods=len(output.values), freq=aliases[output.frequency]
        ).to_timestamp()
        columns[name] = pd.Series(output.values, index=index)
    return pd.DataFrame(columns)


def _pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as error:
        raise ImportError(
            "pandas is missing; reinstall demetrapy"
        ) from error
    return pd


def _validate_frame(frame: Any, label: str, pd: Any) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"{label} must be a pandas DataFrame or Series")
    if frame.empty or not len(frame.columns):
        raise ValueError(f"{label} must not be empty")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError(f"{label} must use a DatetimeIndex")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{label} index must be unique and increasing")
    if not frame.columns.is_unique:
        raise ValueError(f"{label} columns must be unique")
    for column in frame.columns:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"{label} column '{column}' must be numeric")
        if not frame[column].map(math.isfinite).all():
            raise ValueError(f"{label} column '{column}' must contain finite values")


def _frequency_and_periods(index: Any, label: str, pd: Any) -> tuple[str, Any]:
    if len(index) < 3 or pd.infer_freq(index) is None:
        raise ValueError(f"{label} index must have a regular supported frequency")
    month_numbers = index.year * 12 + index.month
    month_steps = set(month_numbers[1:] - month_numbers[:-1])
    if len(month_steps) != 1:
        raise ValueError(f"{label} index must have a regular supported frequency")
    frequency = _FREQUENCIES.get(month_steps.pop())
    if frequency is None:
        raise ValueError(f"{label} frequency must be monthly, quarterly, half-yearly, or yearly")
    aliases = {
        "Monthly": "M",
        "Quarterly": "Q-DEC",
        "HalfYearly": "2Q-DEC",
        "Yearly": "Y-DEC",
    }
    return frequency, index.to_period(aliases[frequency])


def _start_period(period: Any, frequency: str) -> int:
    divisors = {"Monthly": 1, "Quarterly": 3, "HalfYearly": 6, "Yearly": 12}
    return (period.start_time.month - 1) // divisors[frequency] + 1


def _column_list(columns: Any) -> str:
    return ", ".join(sorted(str(column) for column in columns))
