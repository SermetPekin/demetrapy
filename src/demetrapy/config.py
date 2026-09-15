from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Union


FREQUENCIES = ("Monthly", "Quarterly", "HalfYearly", "Yearly")
METHOD_SPECIFICATIONS = {
    "x13": ("RSAX11", "RSA0", "RSA1", "RSA2", "RSA3", "RSA4", "RSA5"),
    "tramoseats": ("RSA0", "RSA1", "RSA2", "RSA3", "RSA4", "RSA5", "RSAfull"),
}
X11_OPTIONS = (
    "decomposition_mode",
    "seasonal_filter",
    "henderson_filter_length",
    "lower_sigma",
    "upper_sigma",
    "forecast_horizon",
    "backcast_horizon",
)


@dataclass(frozen=True)
class X13Config:
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
    calendar: dict[str, Any] | None = None
    user_variables: list[dict[str, Any]] = field(default_factory=list)
    outliers: list[dict[str, Any]] = field(default_factory=list)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    ramps: list[dict[str, Any]] = field(default_factory=list)
    fixed_coefficients: dict[str, float | list[float]] = field(default_factory=dict)
    preprocessing: dict[str, Any] | None = None
    outlier_detection: dict[str, Any] | None = None

    def to_adjustment_config(self) -> "AdjustmentConfig":
        config = AdjustmentConfig(method="x13", **asdict(self))
        config.validate()
        return config

    def validate(self) -> None:
        self.to_adjustment_config()

    def to_dict(self, *, omit_empty: bool = False) -> dict[str, Any]:
        return self.to_adjustment_config().to_dict(omit_empty=omit_empty)


@dataclass(frozen=True)
class TramoSeatsConfig:
    frequency: str = "Monthly"
    spec: str = "RSA4"
    date_column: str = "date"
    value_column: str = "value"
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

    def to_adjustment_config(self) -> "AdjustmentConfig":
        config = AdjustmentConfig(method="tramoseats", **asdict(self))
        config.validate()
        return config

    def validate(self) -> None:
        self.to_adjustment_config()

    def to_dict(self, *, omit_empty: bool = False) -> dict[str, Any]:
        return self.to_adjustment_config().to_dict(omit_empty=omit_empty)


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
            config = cls(**payload)
        except TypeError as error:
            raise ValueError(f"invalid config: {error}") from error
        config.validate()
        return config

    @classmethod
    def template(cls, method: str) -> "AdjustmentConfig":
        normalized = method.lower()
        if normalized == "x13":
            return cls(
                method="x13",
                spec="RSA4",
                forecast_horizon=12,
                calendar={
                    "type": "WorkingDays",
                    "length_of_period": "LeapYear",
                    "test": "Add",
                },
                outlier_detection={"types": ["AO", "LS", "TC"]},
            )
        if normalized == "tramoseats":
            return cls(
                method="tramoseats",
                spec="RSA4",
                preprocessing={"automodel": {"enabled": True}},
                calendar={
                    "type": "WorkingDays",
                    "leap_year": True,
                    "test": "Separate_T",
                },
                outlier_detection={"types": ["AO", "LS", "TC"]},
                seats={"prediction_length": 12},
            )
        raise ValueError("method must be 'x13' or 'tramoseats'")

    def validate(self) -> None:
        if self.frequency not in FREQUENCIES:
            raise ValueError(
                f"frequency must be one of {', '.join(FREQUENCIES)}"
            )
        if self.method not in METHOD_SPECIFICATIONS:
            raise ValueError("method must be 'x13' or 'tramoseats'")
        if self.spec not in METHOD_SPECIFICATIONS[self.method]:
            raise ValueError(
                f"unsupported {self.method} specification: {self.spec}"
            )
        if not isinstance(self.date_column, str) or not self.date_column:
            raise ValueError("date_column must be a non-empty string")
        if not isinstance(self.value_column, str) or not self.value_column:
            raise ValueError("value_column must be a non-empty string")
        if not isinstance(self.benchmarking, bool):
            raise ValueError("benchmarking must be a boolean")
        if self.method != "x13" and any(
            getattr(self, name) is not None for name in X11_OPTIONS
        ):
            raise ValueError("X11 options can only be used with method='x13'")
        if self.seats and self.method != "tramoseats":
            raise ValueError("seats options require method='tramoseats'")

        self._validate_mapping(self.preprocessing, "preprocessing")
        self._validate_mapping(self.calendar, "calendar")
        self._validate_mapping(self.outlier_detection, "outlier_detection")
        self._validate_mapping(self.seats, "seats")
        self._validate_preprocessing()
        self._validate_calendar()
        self._validate_outlier_detection()
        self._validate_seats()

        for name in ("user_variables", "outliers", "interventions", "ramps"):
            values = getattr(self, name)
            if not isinstance(values, list) or not all(
                isinstance(value, dict) for value in values
            ):
                raise ValueError(f"{name} must be a list of objects")
        for variable in self.user_variables:
            if not variable.get("name"):
                raise ValueError("each user variable needs a name")
            if "column" not in variable and "values" not in variable:
                raise ValueError(
                    f"user variable '{variable['name']}' needs a column or values"
                )

    @staticmethod
    def _validate_mapping(value: Any, name: str) -> None:
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object")

    def _validate_preprocessing(self) -> None:
        preprocessing = self.preprocessing or {}
        self._reject_unknown(
            preprocessing,
            {"transform", "automodel", "arima", "estimate"},
            "preprocessing sections",
        )
        for section in preprocessing:
            self._validate_mapping(preprocessing[section], f"preprocessing.{section}")

        transform = preprocessing.get("transform", {})
        transform_keys = {"function"}
        transform_keys.update(
            {"aic_difference", "constant", "adjust"}
            if self.method == "x13"
            else {"fct", "units", "preliminary_check"}
        )
        self._reject_unknown(transform, transform_keys, "transform options")

        arima = preprocessing.get("arima", {})
        self._reject_unknown(
            arima, {"p", "d", "q", "bp", "bd", "bq", "mean"}, "ARIMA options"
        )
        for name in ("p", "d", "q", "bp", "bd", "bq"):
            if name in arima and (
                isinstance(arima[name], bool)
                or not isinstance(arima[name], int)
                or arima[name] < 0
            ):
                raise ValueError(f"ARIMA order '{name}' must be a non-negative integer")
        if "mean" in arima and not isinstance(arima["mean"], bool):
            raise ValueError("ARIMA option 'mean' must be a boolean")

        automodel_keys = {"enabled", "accept_default"}
        automodel_keys.update(
            {
                "check_mu", "mixed", "balanced", "ljung_box_limit",
                "arma_significance", "percent_rse", "hannan_rissanen",
                "percent_reduction_cv", "initial_unit_root_limit",
                "final_unit_root_limit", "cancelation_limit", "unit_root_limit",
            }
            if self.method == "x13"
            else {"pcr", "ub1", "ub2", "cancel", "tsig", "pc", "ami_compare"}
        )
        self._reject_unknown(
            preprocessing.get("automodel", {}), automodel_keys, "automodel options"
        )
        estimate_keys = {"tolerance"}
        if self.method == "tramoseats":
            estimate_keys.update({"exact_ml", "unit_root_limit"})
        self._reject_unknown(
            preprocessing.get("estimate", {}), estimate_keys, "estimate options"
        )

    def _validate_calendar(self) -> None:
        calendar = self.calendar or {}
        keys = {
            "type", "test", "stock_day", "holidays", "custom_holidays",
            "easter", "mean_correction", "julian_easter",
        }
        keys.update(
            {"length_of_period"}
            if self.method == "x13"
            else {"leap_year", "automatic"}
        )
        self._reject_unknown(calendar, keys, f"{self.method} calendar options")

    def _validate_outlier_detection(self) -> None:
        keys = {"types", "critical_value", "tc_rate"}
        keys.update(
            {"ls_run", "max_iterations"}
            if self.method == "x13"
            else {"exact_ml"}
        )
        self._reject_unknown(
            self.outlier_detection or {}, keys, "outlier detection options"
        )

    def _validate_seats(self) -> None:
        self._reject_unknown(
            self.seats or {},
            {
                "approximation_mode", "estimation_method", "xl_boundary",
                "seasonal_tolerance", "trend_boundary", "seasonal_boundary",
                "seasonal_boundary_at_pi", "prediction_length",
            },
            "SEATS options",
        )

    @staticmethod
    def _reject_unknown(values: dict[str, Any], allowed: set[str], label: str) -> None:
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unsupported {label}: {', '.join(sorted(unknown))}")

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

    def to_dict(self, *, omit_empty: bool = False) -> dict[str, Any]:
        values = asdict(self)
        if not omit_empty:
            return values
        return {
            name: value
            for name, value in values.items()
            if value is not None and value != [] and value != {}
        }


Config = Union[AdjustmentConfig, X13Config, TramoSeatsConfig]


def normalize_config(config: Config) -> AdjustmentConfig:
    if isinstance(config, AdjustmentConfig):
        config.validate()
        return config
    return config.to_adjustment_config()