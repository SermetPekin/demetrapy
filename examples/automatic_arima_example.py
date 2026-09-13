"""Run both engines with automatic ARIMA model selection."""

from __future__ import annotations

import math
import random

from seasonal_pri import adjust


def create_values() -> list[float]:
    random_source = random.Random(20260914)
    seasonal_pattern = (-7.0, -4.0, -1.0, 2.0, 5.0, 8.0, 9.0, 5.0, 1.0, -2.0, -6.0, -10.0)
    return [
        120.0
        + 0.18 * index
        + 2.5 * math.sin(index / 20.0)
        + seasonal_pattern[index % 12]
        + random_source.gauss(0.0, 1.0)
        for index in range(180)
    ]


if __name__ == "__main__":
    values = create_values()
    for method in ("x13", "tramoseats"):
        result = adjust(
            values,
            start_year=2010,
            method=method,
            spec="RSA4",
            preprocessing={"automodel": {"enabled": True}},
            detailed=True,
        )
        model = result.arima_model
        if model is None:
            raise RuntimeError(f"{method} did not report a fitted ARIMA model")
        print(
            f"{method}: {model.notation}, mean={model.mean}, "
            f"automatic={model.automatic}"
        )