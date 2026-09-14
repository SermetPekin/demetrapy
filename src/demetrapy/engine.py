from __future__ import annotations

from dataclasses import dataclass, field
import keyword
import os
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

import jpype

from .config import Config, normalize_config
import jpype.imports

JDEMETRA_VERSION = "2.2.6"
JAR_URL = (
    "https://repo1.maven.org/maven2/eu/europa/ec/joinup/sat/"
    f"demetra-tstoolkit/{JDEMETRA_VERSION}/demetra-tstoolkit-{JDEMETRA_VERSION}.jar"
)
RESULT_SCHEMA_VERSION = 2
COMPACT_COMPONENTS = ("y", "ycal", "sa", "t", "s", "i")
FORECAST_COMPONENTS = ("y_f", "ycal_f", "sa_f", "t_f", "s_f", "i_f")
_PERIODS_PER_YEAR = {"Monthly": 12, "Quarterly": 4, "HalfYearly": 2, "Yearly": 1}


@dataclass(frozen=True)
class OutputSeries:
    values: tuple[float, ...]
    frequency: str
    start_year: int
    start_period: int


@dataclass(frozen=True)
class AdjustmentComponents:
    observed: OutputSeries
    calendar_adjusted: OutputSeries
    seasonally_adjusted: OutputSeries
    trend: OutputSeries
    seasonal: OutputSeries
    irregular: OutputSeries

    def __getitem__(self, name: str) -> OutputSeries:
        aliases = {
            "y": "observed",
            "ycal": "calendar_adjusted",
            "sa": "seasonally_adjusted",
            "t": "trend",
            "s": "seasonal",
            "i": "irregular",
        }
        attribute = aliases.get(name, name)
        if attribute not in self.__dataclass_fields__:
            raise KeyError(name)
        return getattr(self, attribute)

    def to_compact_dict(self) -> dict[str, list[float]]:
        return {
            name: list(self[name].values)
            for name in COMPACT_COMPONENTS
        }


@dataclass(frozen=True)
class AdjustmentForecasts:
    observed: OutputSeries | None = None
    calendar_adjusted: OutputSeries | None = None
    seasonally_adjusted: OutputSeries | None = None
    trend: OutputSeries | None = None
    seasonal: OutputSeries | None = None
    irregular: OutputSeries | None = None

    def __getitem__(self, name: str) -> OutputSeries | None:
        aliases = {
            "y_f": "observed",
            "ycal_f": "calendar_adjusted",
            "sa_f": "seasonally_adjusted",
            "t_f": "trend",
            "s_f": "seasonal",
            "i_f": "irregular",
        }
        attribute = aliases.get(name, name)
        if attribute not in self.__dataclass_fields__:
            raise KeyError(name)
        return getattr(self, attribute)

    def to_compact_dict(self) -> dict[str, list[float]]:
        return {
            name: list(output.values)
            for name in FORECAST_COMPONENTS
            if (output := self[name]) is not None
        }


@dataclass(frozen=True)
class ProcessingMessage:
    type: str
    name: str
    origin: str
    message: str


@dataclass(frozen=True)
class ArimaModel:
    p: int
    d: int
    q: int
    bp: int
    bd: int
    bq: int
    period: int
    mean: bool
    automatic: bool

    @property
    def notation(self) -> str:
        return (
            f"ARIMA({self.p},{self.d},{self.q})"
            f"({self.bp},{self.bd},{self.bq})[{self.period}]"
        )


@dataclass(frozen=True)
class AdjustmentResult:
    components: AdjustmentComponents
    method: str
    specification: str
    series: Mapping[str, OutputSeries]
    diagnostics: Mapping[str, bool | float | int | str]
    messages: tuple[ProcessingMessage, ...]
    forecasts: AdjustmentForecasts = field(default_factory=AdjustmentForecasts)
    arima_model: ArimaModel | None = None

    @property
    def observed(self) -> OutputSeries:
        return self.components.observed

    @property
    def seasonally_adjusted(self) -> OutputSeries:
        return self.components.seasonally_adjusted

    @property
    def calendar_adjusted(self) -> OutputSeries:
        return self.components.calendar_adjusted

    @property
    def trend(self) -> OutputSeries:
        return self.components.trend

    @property
    def seasonal(self) -> OutputSeries:
        return self.components.seasonal

    @property
    def irregular(self) -> OutputSeries:
        return self.components.irregular

    def to_compact_dict(self) -> dict[str, list[float]]:
        return self.components.to_compact_dict()

    def to_forecast_dict(self) -> dict[str, list[float]]:
        return self.forecasts.to_compact_dict()


def _jar_path() -> Path:
    configured = os.environ.get("DEMETRAPY_JAR")
    if configured:
        jar = Path(configured).expanduser()
        if not jar.is_file():
            raise FileNotFoundError(
                f"DEMETRAPY_JAR does not point to a file: {jar}. "
                "Unset it to use the automatic JAR download."
            )
        return jar
    return Path.home() / ".cache" / "demetrapy" / Path(JAR_URL).name


def _ensure_jvm() -> None:
    if jpype.isJVMStarted():
        return

    jar = _jar_path()
    if not jar.exists():
        jar.parent.mkdir(parents=True, exist_ok=True)
        temporary = jar.with_suffix(".tmp")
        urllib.request.urlretrieve(JAR_URL, temporary)
        temporary.replace(jar)
    jpype.startJVM(classpath=[str(jar)])


def adjust(
    values: Sequence[float],
    *,
    config: Config | None = None,
    frequency: str = "Monthly",
    start_year: int,
    start_period: int = 1,
    method: str = "x13",
    spec: str = "RSA4",
    decomposition_mode: str | None = None,
    seasonal_filter: str | None = None,
    henderson_filter_length: int | None = None,
    lower_sigma: float | None = None,
    upper_sigma: float | None = None,
    forecast_horizon: int | None = None,
    backcast_horizon: int | None = None,
    benchmarking: bool = False,
    user_variables: Sequence[Mapping[str, Any]] = (),
    calendar_variables: Sequence[Mapping[str, Any]] = (),
    calendar: Mapping[str, Any] | None = None,
    outliers: Sequence[Mapping[str, Any]] = (),
    interventions: Sequence[Mapping[str, Any]] = (),
    ramps: Sequence[Mapping[str, Any]] = (),
    fixed_coefficients: Mapping[str, float | Sequence[float]] | None = None,
    preprocessing: Mapping[str, Any] | None = None,
    outlier_detection: Mapping[str, Any] | None = None,
    seats: Mapping[str, Any] | None = None,
    detailed: bool = False,
) -> AdjustmentResult:
    """Seasonally adjust one regular series using X13 or TRAMO/SEATS."""
    if config is not None:
        normalized = normalize_config(config)
        configured = normalized.engine_options()
        supplied = {
            "frequency": frequency,
            "method": method,
            "spec": spec,
            "decomposition_mode": decomposition_mode,
            "seasonal_filter": seasonal_filter,
            "henderson_filter_length": henderson_filter_length,
            "lower_sigma": lower_sigma,
            "upper_sigma": upper_sigma,
            "forecast_horizon": forecast_horizon,
            "backcast_horizon": backcast_horizon,
            "benchmarking": benchmarking,
            "user_variables": user_variables,
            "calendar": calendar,
            "outliers": outliers,
            "interventions": interventions,
            "ramps": ramps,
            "fixed_coefficients": fixed_coefficients,
            "preprocessing": preprocessing,
            "outlier_detection": outlier_detection,
            "seats": seats,
        }
        defaults = {
            "frequency": "Monthly",
            "method": "x13",
            "spec": "RSA4",
            "decomposition_mode": None,
            "seasonal_filter": None,
            "henderson_filter_length": None,
            "lower_sigma": None,
            "upper_sigma": None,
            "forecast_horizon": None,
            "backcast_horizon": None,
            "benchmarking": False,
            "user_variables": (),
            "calendar": None,
            "outliers": (),
            "interventions": (),
            "ramps": (),
            "fixed_coefficients": None,
            "preprocessing": None,
            "outlier_detection": None,
            "seats": None,
        }
        conflicts = sorted(
            name
            for name, value in supplied.items()
            if value != defaults[name] and value != configured[name]
        )
        if conflicts:
            raise ValueError(
                "config conflicts with adjustment options: " + ", ".join(conflicts)
            )
        return adjust(
            values,
            start_year=start_year,
            start_period=start_period,
            calendar_variables=calendar_variables,
            detailed=detailed,
            **configured,
        )
    if not values:
        raise ValueError("values must not be empty")
    if frequency not in _PERIODS_PER_YEAR:
        raise ValueError(f"unsupported frequency: {frequency}")
    _validate_start_period(start_period, frequency, "series")

    _ensure_jvm()
    TsData = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsData")
    TsFrequency = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsFrequency")
    DecompositionMode = jpype.JClass("ec.satoolkit.DecompositionMode")
    SeasonalFilterOption = jpype.JClass("ec.satoolkit.x11.SeasonalFilterOption")

    java_frequency = getattr(TsFrequency, frequency)
    data = TsData(
        java_frequency,
        start_year,
        start_period - 1,
        jpype.JArray(jpype.JDouble)(values),
        False,
    )
    context, descriptors, calendar_variable_names = _processing_context(
        user_variables,
        calendar_variables,
        java_frequency,
        start_year,
        start_period,
        len(values),
    )
    java_spec, factory = _specification(
        method,
        spec,
        descriptors,
        decomposition_mode=decomposition_mode,
        seasonal_filter=seasonal_filter,
        henderson_filter_length=henderson_filter_length,
        lower_sigma=lower_sigma,
        upper_sigma=upper_sigma,
        forecast_horizon=forecast_horizon,
        backcast_horizon=backcast_horizon,
        benchmarking=benchmarking,
        calendar=calendar,
        calendar_variable_names=calendar_variable_names,
        outliers=outliers,
        interventions=interventions,
        ramps=ramps,
        fixed_coefficients=fixed_coefficients or {},
        user_variables=user_variables,
        preprocessing=preprocessing,
        outlier_detection=outlier_detection,
        seats=seats,
        DecompositionMode=DecompositionMode,
        SeasonalFilterOption=SeasonalFilterOption,
    )
    _register_calendar(context, calendar)
    results = factory.process(data, java_spec, context)

    return _adjustment_result(
        results,
        method,
        spec,
        TsData,
        _uses_auto_model(java_spec, method),
        detailed,
    )


def _adjustment_result(
    results: Any,
    method: str,
    specification: str,
    TsData: Any,
    automatic: bool,
    detailed: bool,
) -> AdjustmentResult:
    component_values = {}
    component_keys = {
        "y": "y",
        "ycal": "preprocessing.ycal",
        "sa": "sa",
        "t": "t",
        "s": "s",
        "i": "i",
    }
    for name, result_key in component_keys.items():
        value = results.getData(result_key, TsData.class_)
        if value is None:
            information = "; ".join(str(item) for item in results.getProcessingInformation())
            detail = f": {information}" if information else ""
            raise RuntimeError(
                f"JDemetra+ did not produce the '{result_key}' series{detail}"
            )
        component_values[name] = _output_series(value)
    components = AdjustmentComponents(
        observed=component_values["y"],
        calendar_adjusted=component_values["ycal"],
        seasonally_adjusted=component_values["sa"],
        trend=component_values["t"],
        seasonal=component_values["s"],
        irregular=component_values["i"],
    )
    forecasts = AdjustmentForecasts(
        observed=_optional_output_series(results, "final.y_f", TsData),
        calendar_adjusted=_optional_output_series(
            results, "preprocessing.ycal_f", TsData
        ),
        seasonally_adjusted=_optional_output_series(results, "final.sa_f", TsData),
        trend=_optional_output_series(results, "final.t_f", TsData),
        seasonal=_optional_output_series(results, "final.s_f", TsData),
        irregular=_optional_output_series(results, "final.i_f", TsData),
    )

    if not detailed:
        return AdjustmentResult(
            components=components,
            forecasts=forecasts,
            method=method,
            specification=specification,
            series={},
            diagnostics={},
            messages=(),
        )

    series: dict[str, OutputSeries] = {}
    diagnostics: dict[str, bool | float | int | str] = {}
    for java_name, java_type in results.getDictionary().entrySet():
        name = str(java_name)
        if java_type == TsData.class_:
            value = results.getData(name, TsData.class_)
            if value is not None:
                series[name] = _output_series(value)
            continue
        class_name = str(java_type.getName())
        if class_name in {
            "boolean",
            "double",
            "int",
            "java.lang.Boolean",
            "java.lang.Double",
            "java.lang.Integer",
            "java.lang.Long",
            "java.lang.String",
        }:
            value = results.getData(name, java_type)
            if value is not None:
                if isinstance(value, (bool, float, int, str)):
                    diagnostics[name] = value
                else:
                    diagnostics[name] = str(value)

    messages = tuple(
        ProcessingMessage(
            type=str(item.type),
            name=str(item.name or ""),
            origin=str(item.origin or ""),
            message=str(item.msg or ""),
        )
        for item in results.getProcessingInformation()
    )
    return AdjustmentResult(
        components=components,
        forecasts=forecasts,
        method=method,
        specification=specification,
        series=series,
        diagnostics=diagnostics,
        messages=messages,
        arima_model=_arima_model(results, diagnostics, automatic),
    )


def _output_series(value: Any) -> OutputSeries:
    start = value.getStart()
    return OutputSeries(
        values=tuple(float(item) for item in value.internalStorage()),
        frequency=str(value.getFrequency()),
        start_year=int(start.getYear()),
        start_period=int(start.getPosition()) + 1,
    )


def _optional_output_series(
    results: Any, name: str, TsData: Any
) -> OutputSeries | None:
    value = results.getData(name, TsData.class_)
    if value is None:
        return None
    output = _output_series(value)
    return output if output.values else None


def _arima_model(
    results: Any,
    diagnostics: Mapping[str, bool | float | int | str],
    automatic: bool,
) -> ArimaModel | None:
    SarimaModel = jpype.JClass("ec.tstoolkit.sarima.SarimaModel")
    fitted = results.getData("preprocessing.arima", SarimaModel.class_)
    if fitted is None:
        return None
    model = fitted.getSpecification()
    return ArimaModel(
        p=int(model.getP()),
        d=int(model.getD()),
        q=int(model.getQ()),
        bp=int(model.getBP()),
        bd=int(model.getBD()),
        bq=int(model.getBQ()),
        period=int(fitted.getFrequency()),
        mean=bool(diagnostics.get("preprocessing.arima.mean", False)),
        automatic=automatic,
    )


def _uses_auto_model(java_spec: Any, method: str) -> bool:
    normalized = method.lower().replace("-", "").replace("/", "")
    preprocessing = (
        java_spec.getRegArimaSpecification()
        if normalized == "x13"
        else java_spec.getTramoSpecification()
    )
    return bool(preprocessing.isUsingAutoModel())


def _processing_context(
    variables: Sequence[Mapping[str, Any]],
    calendar_variables: Sequence[Mapping[str, Any]],
    frequency: Any,
    start_year: int,
    start_period: int,
    expected_length: int,
) -> tuple[Any, list[Any], list[str]]:
    ProcessingContext = jpype.JClass("ec.tstoolkit.algorithm.ProcessingContext")
    TsData = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsData")
    TsVariable = jpype.JClass("ec.tstoolkit.timeseries.regression.TsVariable")
    TsVariables = jpype.JClass("ec.tstoolkit.timeseries.regression.TsVariables")
    TsVariableDescriptor = jpype.JClass("ec.tstoolkit.modelling.TsVariableDescriptor")
    UserComponentType = jpype.JClass(
        "ec.tstoolkit.modelling.TsVariableDescriptor$UserComponentType"
    )

    context = ProcessingContext()
    groups: dict[str, Any] = {}
    registered_names: set[tuple[str, str]] = set()
    descriptors: list[Any] = []
    for variable in variables:
        name = str(variable.get("name", "")).strip()
        if not name or "." in name:
            raise ValueError("each user variable needs a name without dots")
        group = str(variable.get("group", "user")).strip()
        if not group or "." in group:
            raise ValueError("user variable groups must be non-empty and contain no dots")
        _reserve_variable_name(registered_names, group, name)
        variable_values = variable.get("values")
        if not isinstance(variable_values, Sequence) or isinstance(variable_values, str):
            raise ValueError(f"user variable '{name}' needs a values sequence")
        if len(variable_values) != expected_length:
            raise ValueError(f"user variable '{name}' must match values length")

        manager = groups.setdefault(group, TsVariables())
        variable_data = TsData(
            frequency,
            start_year,
            start_period - 1,
            jpype.JArray(jpype.JDouble)(variable_values),
            False,
        )
        manager.set(name, TsVariable(name, variable_data))

        descriptor = TsVariableDescriptor(f"{group}.{name}")
        descriptor.setLags(int(variable.get("first_lag", 0)), int(variable.get("last_lag", 0)))
        try:
            descriptor.setEffect(getattr(UserComponentType, variable.get("effect", "Undefined")))
        except AttributeError as error:
            raise ValueError(f"unsupported user variable effect: {variable.get('effect')}") from error
        descriptors.append(descriptor)

    calendar_variable_names: list[str] = []
    for variable in calendar_variables:
        name = str(variable.get("name", "")).strip()
        if not name or "." in name:
            raise ValueError("each calendar variable needs a name without dots")
        group = str(variable.get("group", "calendar")).strip()
        if not group or "." in group:
            raise ValueError("calendar variable groups must contain no dots")
        _reserve_variable_name(registered_names, group, name)
        variable_values = variable.get("values")
        if (
            not isinstance(variable_values, Sequence)
            or isinstance(variable_values, str)
            or not variable_values
        ):
            raise ValueError(f"calendar variable '{name}' needs a non-empty values sequence")
        variable_frequency = frequency
        if "frequency" in variable:
            TsFrequency = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsFrequency")
            variable_frequency_name = str(variable["frequency"])
            if variable_frequency_name not in _PERIODS_PER_YEAR:
                raise ValueError(f"unsupported frequency for calendar variable '{name}'")
            variable_frequency = getattr(TsFrequency, variable_frequency_name)
        else:
            variable_frequency_name = str(frequency)
        if "start_year" not in variable:
            raise ValueError(f"calendar variable '{name}' needs start_year")
        variable_start_period = int(variable.get("start_period", 1))
        _validate_start_period(
            variable_start_period,
            variable_frequency_name,
            f"calendar variable '{name}'",
        )

        manager = groups.setdefault(group, TsVariables())
        variable_data = TsData(
            variable_frequency,
            int(variable["start_year"]),
            variable_start_period - 1,
            jpype.JArray(jpype.JDouble)(variable_values),
            False,
        )
        manager.set(name, TsVariable(name, variable_data))
        if bool(variable.get("selected", True)):
            calendar_variable_names.append(f"{group}.{name}")

    for group, manager in groups.items():
        context.getTsVariableManagers().set(group, manager)
    return context, descriptors, calendar_variable_names


def _reserve_variable_name(
    registered_names: set[tuple[str, str]], group: str, name: str
) -> None:
    identifier = (group, name)
    if identifier in registered_names:
        raise ValueError(f"variable name is already registered: {group}.{name}")
    registered_names.add(identifier)


def _validate_start_period(start_period: int, frequency: str, label: str) -> None:
    maximum = _PERIODS_PER_YEAR[frequency]
    if not 1 <= start_period <= maximum:
        raise ValueError(
            f"{label} start_period must be between 1 and {maximum} for {frequency}"
        )


def _specification(
    method: str,
    spec: str,
    descriptors: Sequence[Any],
    **options: Any,
) -> tuple[Any, Any]:
    normalized = method.lower().replace("-", "").replace("/", "")
    if normalized == "x13":
        Specification = jpype.JClass("ec.satoolkit.x13.X13Specification")
        Factory = jpype.JClass("ec.satoolkit.algorithm.implementation.X13ProcessingFactory")
        method_name = "X13"
    elif normalized in {"tramoseats", "ts"}:
        Specification = jpype.JClass("ec.satoolkit.tramoseats.TramoSeatsSpecification")
        Factory = jpype.JClass(
            "ec.satoolkit.algorithm.implementation.TramoSeatsProcessingFactory"
        )
        method_name = "TRAMO/SEATS"
    else:
        raise ValueError("method must be 'x13' or 'tramoseats'")

    try:
        java_spec = getattr(Specification, spec).clone()
    except AttributeError as error:
        raise ValueError(f"unsupported {method_name} specification: {spec}") from error

    regression = (
        java_spec.getRegArimaSpecification().getRegression()
        if normalized == "x13"
        else java_spec.getTramoSpecification().getRegression()
    )
    for descriptor in descriptors:
        regression.add(descriptor)
    _apply_special_variables(regression, options)
    _apply_calendar(
        regression,
        normalized,
        options["calendar"],
        options["calendar_variable_names"],
    )
    _apply_model_options(java_spec, normalized, options)

    if normalized == "x13":
        x11 = java_spec.getX11Specification()
        try:
            if options["decomposition_mode"] is not None:
                x11.setMode(getattr(options["DecompositionMode"], options["decomposition_mode"]))
            if options["seasonal_filter"] is not None:
                x11.setSeasonalFilter(
                    getattr(options["SeasonalFilterOption"], options["seasonal_filter"])
                )
        except AttributeError as error:
            raise ValueError(f"unsupported X11 option: {error}") from error
        for key, setter in (
            ("henderson_filter_length", x11.setHendersonFilterLength),
            ("lower_sigma", x11.setLowerSigma),
            ("upper_sigma", x11.setUpperSigma),
            ("forecast_horizon", x11.setForecastHorizon),
            ("backcast_horizon", x11.setBackcastHorizon),
        ):
            if options[key] is not None:
                setter(options[key])
    elif any(
        options[key] is not None
        for key in (
            "decomposition_mode",
            "seasonal_filter",
            "henderson_filter_length",
            "lower_sigma",
            "upper_sigma",
            "forecast_horizon",
            "backcast_horizon",
        )
    ):
        raise ValueError("X11 options can only be used with method='x13'")

    java_spec.getBenchmarkingSpecification().setEnabled(options["benchmarking"])
    return java_spec, Factory


def _enum(class_name: str, value: str) -> Any:
    enum_class = jpype.JClass(class_name)
    attribute = f"{value}_" if keyword.iskeyword(value) else value
    try:
        return getattr(enum_class, attribute)
    except AttributeError as error:
        raise ValueError(f"unsupported {class_name.rsplit('.', 1)[-1]}: {value}") from error


def _day(value: object) -> Any:
    Day = jpype.JClass("ec.tstoolkit.timeseries.Day")
    try:
        return Day.fromString(str(value))
    except Exception as error:
        raise ValueError(f"invalid ISO date: {value}") from error


def _apply_special_variables(regression: Any, options: Mapping[str, Any]) -> None:
    OutlierDefinition = jpype.JClass(
        "ec.tstoolkit.timeseries.regression.OutlierDefinition"
    )
    OutlierType = jpype.JClass("ec.tstoolkit.timeseries.regression.OutlierType")
    InterventionVariable = jpype.JClass(
        "ec.tstoolkit.timeseries.regression.InterventionVariable"
    )
    Ramp = jpype.JClass("ec.tstoolkit.timeseries.regression.Ramp")

    for item in options["outliers"]:
        try:
            regression.add(OutlierDefinition(_day(item["date"]), getattr(OutlierType, item["type"])))
        except KeyError as error:
            raise ValueError(f"outlier is missing {error.args[0]}") from error
        except AttributeError as error:
            raise ValueError(f"unsupported outlier type: {item.get('type')}") from error

    for item in options["interventions"]:
        intervention = InterventionVariable()
        for sequence in item.get("sequences", ()):
            try:
                intervention.add(_day(sequence["start"]), _day(sequence.get("end", sequence["start"])))
            except KeyError as error:
                raise ValueError(f"intervention sequence is missing {error.args[0]}") from error
        if not intervention.getCount():
            raise ValueError("each intervention needs at least one sequence")
        intervention.setDescription(str(item.get("name", "intervention")))
        intervention.setDelta(float(item.get("delta", 0.0)))
        intervention.setDeltaS(float(item.get("seasonal_delta", 0.0)))
        regression.add(intervention)

    for item in options["ramps"]:
        try:
            regression.add(Ramp(_day(item["start"]), _day(item["end"])))
        except KeyError as error:
            raise ValueError(f"ramp is missing {error.args[0]}") from error

    coefficients = dict(options["fixed_coefficients"])
    for variable in options.get("user_variables", ()):
        if "coefficient" in variable:
            coefficients[f"{variable.get('group', 'user')}@{variable['name']}"] = variable[
                "coefficient"
            ]
    for name, value in coefficients.items():
        values = value if isinstance(value, Sequence) and not isinstance(value, str) else [value]
        regression.setFixedCoefficients(
            name.replace(".", "@"), jpype.JArray(jpype.JDouble)(values)
        )


def _apply_calendar(
    regression: Any,
    method: str,
    calendar: Mapping[str, Any] | None,
    variable_names: Sequence[str],
) -> None:
    if not calendar and not variable_names:
        return
    calendar = calendar or {}
    common_options = {
        "type",
        "test",
        "stock_day",
        "holidays",
        "custom_holidays",
        "easter",
        "mean_correction",
        "julian_easter",
    }
    method_options = {"length_of_period"} if method == "x13" else {"leap_year", "automatic"}
    unknown = set(calendar) - common_options - method_options
    if unknown:
        raise ValueError(
            f"unsupported {method} calendar options: {', '.join(sorted(unknown))}"
        )
    if method == "x13":
        trading_days = regression.getTradingDays()
        if "type" in calendar:
            trading_days.setTradingDaysType(
                _enum("ec.tstoolkit.timeseries.calendars.TradingDaysType", calendar["type"])
            )
        if "length_of_period" in calendar:
            trading_days.setLengthOfPeriod(
                _enum(
                    "ec.tstoolkit.timeseries.calendars.LengthOfPeriodType",
                    calendar["length_of_period"],
                )
            )
        if "test" in calendar:
            trading_days.setTest(
                _enum("ec.tstoolkit.modelling.RegressionTestSpec", calendar["test"])
            )
        if "stock_day" in calendar:
            trading_days.setStockTradingDays(int(calendar["stock_day"]))
        if calendar.get("holidays") or calendar.get("custom_holidays"):
            trading_days.setHolidays(str(calendar.get("holidays", "custom")))
        _apply_x13_easter(regression, calendar.get("easter"))
        if variable_names:
            trading_days.disable()
            trading_days.setUserVariables(jpype.JArray(jpype.JString)(variable_names))
    else:
        calendar_spec = regression.getCalendar()
        trading_days = calendar_spec.getTradingDays()
        if "type" in calendar:
            trading_days.setTradingDaysType(
                _enum("ec.tstoolkit.timeseries.calendars.TradingDaysType", calendar["type"])
            )
        if "leap_year" in calendar:
            trading_days.setLeapYear(bool(calendar["leap_year"]))
        if "test" in calendar:
            trading_days.setRegressionTestType(
                _enum("ec.tstoolkit.modelling.RegressionTestType", calendar["test"])
            )
            trading_days.setTest(calendar["test"] != "None")
        if "automatic" in calendar:
            trading_days.setAutomatic(bool(calendar["automatic"]))
        if "stock_day" in calendar:
            trading_days.setStockTradingDays(int(calendar["stock_day"]))
        if calendar.get("holidays") or calendar.get("custom_holidays"):
            trading_days.setHolidays(str(calendar.get("holidays", "custom")))
        _apply_tramo_easter(calendar_spec.getEaster(), calendar.get("easter"))
        if variable_names:
            trading_days.disable()
            trading_days.setUserVariables(jpype.JArray(jpype.JString)(variable_names))


def _apply_x13_easter(regression: Any, settings: object) -> None:
    if not settings:
        return
    config = settings if isinstance(settings, Mapping) else {}
    _reject_unknown_options(config, {"test", "julian", "duration"}, "X13 Easter")
    MovingHolidaySpec = jpype.JClass("ec.tstoolkit.modelling.arima.x13.MovingHolidaySpec")
    easter = MovingHolidaySpec.easterSpec(config.get("test", "Add") == "Add", bool(config.get("julian", False)))
    easter.setW(int(config.get("duration", 6)))
    easter.setTest(_enum("ec.tstoolkit.modelling.RegressionTestSpec", config.get("test", "Add")))
    regression.clearMovingHolidays()
    regression.add(easter)


def _apply_tramo_easter(easter: Any, settings: object) -> None:
    if not settings:
        return
    config = settings if isinstance(settings, Mapping) else {}
    _reject_unknown_options(
        config,
        {"option", "duration", "test", "julian"},
        "TRAMO Easter",
    )
    easter.setOption(
        _enum(
            "ec.tstoolkit.modelling.arima.tramo.EasterSpec$Type",
            config.get("option", "Standard"),
        )
    )
    easter.setDuration(int(config.get("duration", 6)))
    easter.setTest(bool(config.get("test", True)))
    easter.setJulian(bool(config.get("julian", False)))


def _register_calendar(context: Any, calendar: Mapping[str, Any] | None) -> None:
    if not calendar or not calendar.get("custom_holidays"):
        return
    NationalCalendar = jpype.JClass("ec.tstoolkit.timeseries.calendars.NationalCalendar")
    NationalCalendarProvider = jpype.JClass(
        "ec.tstoolkit.timeseries.calendars.NationalCalendarProvider"
    )
    FixedDay = jpype.JClass("ec.tstoolkit.timeseries.calendars.FixedDay")
    SpecialCalendarDay = jpype.JClass(
        "ec.tstoolkit.timeseries.calendars.SpecialCalendarDay"
    )
    DayEvent = jpype.JClass("ec.tstoolkit.timeseries.calendars.DayEvent")
    Month = jpype.JClass("ec.tstoolkit.timeseries.Month")

    national_calendar = NationalCalendar(
        bool(calendar.get("mean_correction", True)), bool(calendar.get("julian_easter", False))
    )
    for holiday in calendar["custom_holidays"]:
        weight = float(holiday.get("weight", 1.0))
        if "event" in holiday:
            try:
                special_day = SpecialCalendarDay(
                    getattr(DayEvent, holiday["event"]), int(holiday.get("offset", 0)), weight
                )
            except AttributeError as error:
                raise ValueError(f"unsupported calendar event: {holiday['event']}") from error
        else:
            try:
                special_day = FixedDay(
                    int(holiday["day"]) - 1, Month.valueOf(int(holiday["month"]) - 1), weight
                )
            except KeyError as error:
                raise ValueError(f"fixed holiday is missing {error.args[0]}") from error
        national_calendar.add(special_day)
    context.getGregorianCalendars().set(
        str(calendar.get("holidays", "custom")), NationalCalendarProvider(national_calendar)
    )


def _set_options(target: Any, values: Mapping[str, Any], setters: Mapping[str, str]) -> None:
    unknown = set(values) - set(setters)
    if unknown:
        raise ValueError(f"unsupported options: {', '.join(sorted(unknown))}")
    for key, value in values.items():
        getattr(target, setters[key])(value)


def _reject_unknown_options(
    values: Mapping[str, Any], allowed: set[str], label: str
) -> None:
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"unsupported {label} options: {', '.join(sorted(unknown))}")


def _apply_model_options(java_spec: Any, method: str, options: Mapping[str, Any]) -> None:
    model_options = options["preprocessing"] or {}
    preprocessing = (
        java_spec.getRegArimaSpecification()
        if method == "x13"
        else java_spec.getTramoSpecification()
    )
    unknown = set(model_options) - {"transform", "automodel", "arima", "estimate"}
    if unknown:
        raise ValueError(f"unsupported preprocessing sections: {', '.join(sorted(unknown))}")

    transform_options = model_options.get("transform", {})
    transform = preprocessing.getTransform()
    if "function" in transform_options:
        transform.setFunction(
            _enum(
                "ec.tstoolkit.modelling.DefaultTransformationType",
                transform_options["function"],
            )
        )
    common_transform_keys = {"function"}
    if method == "x13":
        transform_setters = {
            "aic_difference": "setAICDiff",
            "constant": "setConst",
        }
        if "adjust" in transform_options:
            transform.setAdjust(
                _enum(
                    "ec.tstoolkit.timeseries.calendars.LengthOfPeriodType",
                    transform_options["adjust"],
                )
            )
            common_transform_keys.add("adjust")
    else:
        transform_setters = {
            "fct": "setFct",
            "units": "setUnits",
            "preliminary_check": "setPreliminaryCheck",
        }
    _set_options(
        transform,
        {key: value for key, value in transform_options.items() if key not in common_transform_keys},
        transform_setters,
    )

    arima_options = model_options.get("arima", {})
    _validate_arima_options(arima_options)
    _set_options(
        preprocessing.getArima(),
        arima_options,
        {
            "p": "setP",
            "d": "setD",
            "q": "setQ",
            "bp": "setBP",
            "bd": "setBD",
            "bq": "setBQ",
            "mean": "setMean",
        },
    )

    automodel_options = model_options.get("automodel", {})
    automodel = preprocessing.getAutoModel()
    common_automodel = {
        "enabled": "setEnabled",
        "accept_default": "setAcceptDefault",
    }
    method_automodel = (
        {
            "check_mu": "setCheckMu",
            "mixed": "setMixed",
            "balanced": "setBalanced",
            "ljung_box_limit": "setLjungBoxLimit",
            "arma_significance": "setArmaSignificance",
            "percent_rse": "setPercentRSE",
            "hannan_rissanen": "setHannanRissanen",
            "percent_reduction_cv": "setPercentReductionCV",
            "initial_unit_root_limit": "setInitialUnitRootLimit",
            "final_unit_root_limit": "setFinalUnitRootLimit",
            "cancelation_limit": "setCancelationLimit",
            "unit_root_limit": "setUnitRootLimit",
        }
        if method == "x13"
        else {
            "pcr": "setPcr",
            "ub1": "setUb1",
            "ub2": "setUb2",
            "cancel": "setCancel",
            "tsig": "setTsig",
            "pc": "setPc",
            "ami_compare": "setAmiCompare",
        }
    )
    _set_options(automodel, automodel_options, {**common_automodel, **method_automodel})
    if arima_options:
        preprocessing.setUsingAutoModel(False)
    elif "enabled" in automodel_options:
        preprocessing.setUsingAutoModel(bool(automodel_options["enabled"]))

    estimate_setters = {"tolerance": "setTol"}
    if method == "tramoseats":
        estimate_setters.update({"exact_ml": "setEML", "unit_root_limit": "setUbp"})
    _set_options(preprocessing.getEstimate(), model_options.get("estimate", {}), estimate_setters)
    _apply_outlier_detection(preprocessing.getOutliers(), method, options["outlier_detection"])

    seats_options = options["seats"] or {}
    if seats_options and method != "tramoseats":
        raise ValueError("seats options require method='tramoseats'")
    if seats_options:
        seats_spec = java_spec.getSeatsSpecification()
        enum_options = {
            "approximation_mode": (
                "ec.satoolkit.seats.SeatsSpecification$ApproximationMode",
                "setApproximationMode",
            ),
            "estimation_method": (
                "ec.satoolkit.seats.SeatsSpecification$EstimationMethod",
                "setMethod",
            ),
        }
        for key, (class_name, setter) in enum_options.items():
            if key in seats_options:
                getattr(seats_spec, setter)(_enum(class_name, seats_options[key]))
        _set_options(
            seats_spec,
            {key: value for key, value in seats_options.items() if key not in enum_options},
            {
                "xl_boundary": "setXlBoundary",
                "seasonal_tolerance": "setSeasTolerance",
                "trend_boundary": "setTrendBoundary",
                "seasonal_boundary": "setSeasBoundary",
                "seasonal_boundary_at_pi": "setSeasBoundary1",
                "prediction_length": "setPredictionLength",
            },
        )


def _validate_arima_options(options: Mapping[str, Any]) -> None:
    for name in ("p", "d", "q", "bp", "bd", "bq"):
        if name not in options:
            continue
        value = options[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"ARIMA order '{name}' must be a non-negative integer")
    if "mean" in options and not isinstance(options["mean"], bool):
        raise ValueError("ARIMA option 'mean' must be a boolean")


def _apply_outlier_detection(target: Any, method: str, settings: Mapping[str, Any] | None) -> None:
    if not settings:
        return
    target.clearTypes()
    for outlier_type in settings.get("types", ()):
        target.add(_enum("ec.tstoolkit.timeseries.regression.OutlierType", outlier_type))
    ignored = {"types"}
    if method == "x13":
        setters = {
            "critical_value": "setDefaultCriticalValue",
            "tc_rate": "setMonthlyTCRate",
            "ls_run": "setLSRun",
            "max_iterations": "setMaxIter",
        }
    else:
        setters = {
            "critical_value": "setCriticalValue",
            "tc_rate": "setDeltaTC",
            "exact_ml": "setEML",
        }
    _set_options(target, {key: value for key, value in settings.items() if key not in ignored}, setters)