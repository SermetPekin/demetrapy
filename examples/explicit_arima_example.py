"""Run both engines with a user-specified seasonal ARIMA model."""

from __future__ import annotations

from automatic_arima_example import create_values
from seasonal_pri import adjust


if __name__ == "__main__":
    values = create_values()
    arima = {
        "p": 0,
        "d": 1,
        "q": 1,
        "bp": 0,
        "bd": 1,
        "bq": 1,
        "mean": False,
    }
    for method in ("x13", "tramoseats"):
        result = adjust(
            values,
            start_year=2010,
            method=method,
            spec="RSA4",
            preprocessing={"arima": arima},
            detailed=True,
        )
        model = result.arima_model
        if model is None:
            raise RuntimeError(f"{method} did not report a fitted ARIMA model")
        print(
            f"{method}: {model.notation}, mean={model.mean}, "
            f"automatic={model.automatic}"
        )