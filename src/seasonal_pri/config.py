from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdjustmentConfig:
    frequency: str = "Monthly"
    method: str = "x13"
    spec: str = "RSA4"
    date_column: str = "date"
    value_column: str = "value"
    decomposition_mode: str | None = None
    seasonal_filter: str | None = None
    henderson_filter_length: int | None = None
    lower_sigma: float | None = None
    upper_sigma: float | None = None
    forecast_horizon: int | None = None
    backcast_horizon: int | None = None
    benchmarking: bool = False
    calendar: dict[str, Any] | None = None
    user_variables: list[dict[str, Any]] = field(default_factory=list)
    outliers: list[dict[str, Any]] = field(default_factory=list)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    ramps: list[dict[str, Any]] = field(default_factory=list)
    fixed_coefficients: dict[str, float | list[float]] = field(default_factory=dict)
    preprocessing: dict[str, Any] | None = None
    outlier_detection: dict[str, Any] | None = None
    seats: dict[str, Any] | None = None

    @classmethod
    def load(cls, path: str | Path | None) -> "AdjustmentConfig":
        if path is None:
            return cls()
        with Path(path).open(encoding="utf-8") as stream:
            payload: Any = json.load(stream)
        if not isinstance(payload, dict):
            raise ValueError("config must be a JSON object")
        try:
            return cls(**payload)
        except TypeError as error:
            raise ValueError(f"invalid config: {error}") from error

    def engine_options(
        self, user_values: dict[str, list[float]] | None = None
    ) -> dict[str, object]:
        options = asdict(self)
        options.pop("date_column")
        options.pop("value_column")
        variables = []
        for definition in options["user_variables"]:
            variable = dict(definition)
            column = variable.pop("column", None)
            if "values" not in variable:
                if column is None or user_values is None or column not in user_values:
                    raise ValueError(
                        f"user variable '{variable.get('name', '')}' needs a CSV column or values"
                    )
                variable["values"] = user_values[column]
            variables.append(variable)
        options["user_variables"] = variables
        return options

    def user_variable_columns(self) -> list[str]:
        return [
            str(variable["column"])
            for variable in self.user_variables
            if "values" not in variable and "column" in variable
        ]