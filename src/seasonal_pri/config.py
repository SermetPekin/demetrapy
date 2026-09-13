from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdjustmentConfig:
    frequency: str = "Monthly"
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

    def engine_options(self) -> dict[str, object]:
        options = asdict(self)
        options.pop("date_column")
        options.pop("value_column")
        return options