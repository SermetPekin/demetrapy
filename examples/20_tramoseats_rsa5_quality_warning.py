"""Run TRAMO/SEATS RSA5 and warn when review signals are present."""

from __future__ import annotations

import math
import warnings
from typing import Any

from demetrapy import (
    AdjustmentResult,
    TramoSeatsConfig,
    adjust_dataframe,
    load_monthly_tourism,
)


REVIEW_P_VALUE = 0.05

_RESIDUAL_SEASONALITY = (
    "diagnostics.seas-sa-combined",
    "diagnostics.seas-sa-combined3",
    "diagnostics.seas-res-combined",
    "diagnostics.seas-res-combined3",
)

_PVALUE_CHECKS = {
    "diagnostics.seas-res-f": "residual seasonal F test",
    "diagnostics.seas-res-qs": "residual seasonal QS test",
    "diagnostics.seas-res-kw": "residual seasonal Kruskal-Wallis test",
    "diagnostics.seas-res-friedman": "residual seasonal Friedman test",
    "diagnostics.seas-res-periodogram": "residual seasonal periodogram test",
    "diagnostics.td-res-all": "residual trading-day test",
    "diagnostics.td-res-last": "recent residual trading-day test",
    "diagnostics.fcast-outsample-mean": "out-of-sample forecast mean test",
    "diagnostics.fcast-outsample-variance": "out-of-sample forecast variance test",
}

_DECOMPOSITION_FLAGS = {
    "decomposition.parameters_cutoff": "decomposition parameters were truncated",
    "decomposition.model_changed": "the decomposition model was changed",
}


def quality_issues(
    result: AdjustmentResult,
    adjusted: Any,
) -> list[str]:
    """Return review issues reported by JDemetra or visible in adjusted output."""
    issues = []
    for message in result.messages:
        severity = message.type.lower()
        if any(level in severity for level in ("warning", "error", "severe")):
            detail = message.message or message.name or message.type
            issues.append(f"{message.type}: {detail}")

    for name in _RESIDUAL_SEASONALITY:
        value = str(result.diagnostics.get(name, "")).lower().replace(" ", "")
        if value in {"present", "probablypresent"}:
            issues.append(f"residual seasonality reported by {name}: {value}")

    for name, label in _PVALUE_CHECKS.items():
        value = result.diagnostics.get(name)
        if (
            isinstance(value, (float, int))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value < REVIEW_P_VALUE
        ):
            issues.append(f"{label} is significant (p={value:.4g})")

    for name, label in _DECOMPOSITION_FLAGS.items():
        if result.diagnostics.get(name) is True:
            issues.append(label)

    if result.arima_model is None:
        issues.append("fitted ARIMA model metadata is unavailable")
    if adjusted.empty:
        issues.append("seasonally adjusted output is empty")
    elif adjusted.isna().any() or not all(math.isfinite(value) for value in adjusted):
        issues.append("seasonally adjusted output contains missing or non-finite values")
    return issues


def main() -> None:
    data = load_monthly_tourism()
    result = adjust_dataframe(
        data,
        config=TramoSeatsConfig(
            spec="RSA5",
            seats={"prediction_length": 12},
        ),
        detailed=True,
    )

    for target in data.columns:
        target_result = result.for_series(target)
        issues = quality_issues(target_result, result.sa[target])
        if issues:
            warnings.warn(
                f"{target} needs review: {'; '.join(issues)}",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            print(f"{target}: no warning signals reported")

    print("\nSeasonally adjusted tourism:")
    print(result.sa.tail(6).round(2))
    print("\nProcessing status:")
    print(result.status.to_string(index=False))


if __name__ == "__main__":
    main()