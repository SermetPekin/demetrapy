"""Programmatic comparison of seasonal-adjustment configurations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from .config import AdjustmentConfig, Config, TramoSeatsConfig, X13Config
from .dataframe import DataFrameAdjustmentResult, adjust_dataframe


_COMPONENTS = (
    "observed",
    "calendar_adjusted",
    "seasonally_adjusted",
    "trend",
    "seasonal",
    "irregular",
)


@dataclass(frozen=True)
class AdjustmentComparisonResult:
    """Aligned outputs and pairwise metrics for adjustment candidates."""

    components: Any
    metrics: Any
    results: Mapping[str, DataFrameAdjustmentResult]

    def for_candidate(self, label: str) -> DataFrameAdjustmentResult:
        try:
            return self.results[label]
        except KeyError as error:
            raise KeyError(f"unknown comparison candidate: {label}") from error

    def for_series(
        self,
        series: Any,
        component: str = "seasonally_adjusted",
    ) -> Any:
        if component not in _COMPONENTS:
            raise ValueError(f"unknown adjustment component: {component}")
        try:
            return self.components.xs(
                (series, component),
                axis=1,
                level=("series", "component"),
            )
        except KeyError as error:
            raise KeyError(f"unknown comparison series: {series}") from error


def compare_adjustments(
    data: Any,
    candidates: Mapping[str, Config],
    *,
    calendar_pool: Any | None = None,
    user_defined_calendars: Mapping[Any, Sequence[Any]] | None = None,
    detailed: bool = False,
) -> AdjustmentComparisonResult:
    """Run and compare two or more labeled adjustment configurations."""
    pd = _pandas()
    candidate_items = _validate_candidates(candidates)
    results = {
        label: adjust_dataframe(
            data,
            config=config,
            calendar_pool=calendar_pool,
            user_defined_calendars=user_defined_calendars,
            detailed=detailed,
        )
        for label, config in candidate_items
    }
    _validate_targets(results)
    components = pd.concat(
        {label: result.components for label, result in results.items()},
        axis=1,
        names=("candidate", "series", "component"),
    )
    metrics = _comparison_metrics(results, pd)
    return AdjustmentComparisonResult(
        components=components,
        metrics=metrics,
        results=results,
    )


def _validate_candidates(
    candidates: Mapping[str, Config],
) -> list[tuple[str, Config]]:
    if not isinstance(candidates, Mapping):
        raise TypeError("candidates must be a mapping of labels to configurations")
    items = list(candidates.items())
    if len(items) < 2:
        raise ValueError("at least two comparison candidates are required")
    config_types = (AdjustmentConfig, X13Config, TramoSeatsConfig)
    for label, config in items:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("candidate labels must be non-empty strings")
        if not isinstance(config, config_types):
            raise TypeError(f"candidate '{label}' must use a demetrapy configuration")
        config.validate()
    return items


def _validate_targets(results: Mapping[str, DataFrameAdjustmentResult]) -> None:
    expected: tuple[Any, ...] | None = None
    for label, result in results.items():
        targets = tuple(result.results)
        if expected is None:
            expected = targets
        elif targets != expected:
            raise ValueError(f"candidate '{label}' produced different target series")


def _comparison_metrics(
    results: Mapping[str, DataFrameAdjustmentResult],
    pd: Any,
) -> Any:
    rows = []
    labels = list(results)
    targets = list(next(iter(results.values())).results)
    for left_label, right_label in combinations(labels, 2):
        left = results[left_label].components
        right = results[right_label].components
        for target in targets:
            for component in _COMPONENTS:
                aligned = pd.concat(
                    {
                        "left": left[(target, component)],
                        "right": right[(target, component)],
                    },
                    axis=1,
                ).dropna()
                difference = aligned["left"] - aligned["right"]
                rows.append(
                    {
                        "candidate_left": left_label,
                        "candidate_right": right_label,
                        "series": target,
                        "component": component,
                        "observations": len(aligned),
                        "rmse": float((difference.pow(2).mean()) ** 0.5),
                        "max_absolute_difference": float(difference.abs().max()),
                        "mean_difference": float(difference.mean()),
                        "correlation": _correlation(aligned),
                    }
                )
    return pd.DataFrame.from_records(
        rows,
        columns=(
            "candidate_left",
            "candidate_right",
            "series",
            "component",
            "observations",
            "rmse",
            "max_absolute_difference",
            "mean_difference",
            "correlation",
        ),
    )


def _correlation(aligned: Any) -> float:
    if (
        len(aligned) < 2
        or aligned["left"].nunique() < 2
        or aligned["right"].nunique() < 2
    ):
        return float("nan")
    return float(aligned["left"].corr(aligned["right"]))


def _pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as error:
        raise ImportError("pandas is missing; reinstall demetrapy") from error
    return pd